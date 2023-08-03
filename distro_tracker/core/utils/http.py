# Copyright 2013 The Distro Tracker Developers
# See the COPYRIGHT file at the top-level directory of this distribution and
# at https://deb.li/DTAuthors
#
# This file is part of Distro Tracker. It is subject to the license terms
# in the LICENSE file found in the top-level directory of this
# distribution and at https://deb.li/DTLicense. No part of Distro Tracker,
# including this file, may be copied, modified, propagated, or distributed
# except according to the terms contained in the LICENSE file.
"""
Utilities for handling HTTP resource access.
"""

import json
import os
import re
import time
from hashlib import md5

from django.conf import settings
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.http import parse_http_date, url_has_allowed_host_and_scheme

import requests
from requests.structures import CaseInsensitiveDict

from .compression import get_uncompressed_stream, guess_compression_method


def parse_cache_control_header(header):
    """
    Parses the given Cache-Control header's values.

    :returns: The key-value pairs found in the header.
        If some key did not have an associated value in the header, ``None``
        is used instead.
    :rtype: dict
    """
    parts = header.split(',')
    cache_control = {}
    for part in parts:
        part = part.strip()
        if '=' not in part:
            cache_control[part] = None
            continue
        key, value = part.split('=', 1)
        cache_control[key] = value

    return cache_control


class HttpCache(object):
    """
    A class providing an interface to a cache of HTTP responses.
    """
    def __init__(self, cache_directory_path,
                 url_to_cache_path=None):
        self.cache_directory_path = cache_directory_path
        self.custom_url_to_cache_path = url_to_cache_path

    def __contains__(self, item):
        cache_file_name = self._content_cache_file_path(item)
        return os.path.exists(cache_file_name)

    def is_expired(self, url):
        """
        If the cached response for the given URL is expired based on
        Cache-Control or Expires headers, returns True.
        """
        if url not in self:
            return True
        headers = self.get_headers(url)

        # First check if the Cache-Control header has set a max-age
        if 'cache-control' in headers:
            cache_control = parse_cache_control_header(headers['cache-control'])
            if 'max-age' in cache_control:
                max_age = int(cache_control['max-age'])
                response_age = int(
                    os.stat(self._header_cache_file_path(url)).st_mtime)
                current_timestamp = int(time.time())

                return current_timestamp - response_age >= max_age

        # Alternatively, try the Expires header
        if 'expires' in headers:
            expires_date = timezone.datetime.utcfromtimestamp(
                parse_http_date(headers['expires']))
            expires_date = timezone.make_aware(expires_date, timezone.utc)
            current_date = timezone.now()

            return current_date > expires_date

        # If there is no cache freshness date consider the item expired
        return True

    def get_content_stream(self, url, compression="auto", text=False):
        """
        Returns a file-like object that reads the cached copy of the given URL.

        If the file is compressed, the file-like object will read the
        decompressed stream.
        """
        if url in self:
            if compression == "auto":
                compression = guess_compression_method(url)

            # XXX: we leak temp_file... cf skipped test in test suite
            # of get_uncompressed_stream
            temp_file = open(self._content_cache_file_path(url), 'rb')
            return get_uncompressed_stream(temp_file, compression=compression,
                                           text=text)

    def get_content(self, url, compression="auto"):
        """
        Returns the content of the cached response for the given URL.

        If the file is compressed, then uncompress it, else, consider it
        as plain file.

        :param compression: Specifies the compression method used to generate
            the resource, and thus the compression method one should use to
            decompress it.
        :type compression: str

        :rtype: :class:`bytes`

        """
        if url in self:
            with self.get_content_stream(url, compression=compression) as f:
                return f.read()

    def get_headers(self, url):
        """
        Returns the HTTP headers of the cached response for the given URL.

        :rtype: dict
        """
        if url in self:
            with open(self._header_cache_file_path(url), 'r') as header_file:
                return CaseInsensitiveDict(json.load(header_file))
        else:
            return {}

    def remove(self, url):
        """
        Removes the cached response for the given URL.
        """
        if url in self:
            os.remove(self._content_cache_file_path(url))
            os.remove(self._header_cache_file_path(url))

    def update(self, url, force=False, invalidate_cache=True):
        """
        Performs an update of the cached resource. This means that it validates
        that its most current version is found in the cache by doing a
        conditional GET request.

        :param force: To force the method to perform a full GET request, set
            the parameter to ``True``

        :returns: The original HTTP response and a Boolean indicating whether
            the cached value was updated.
        :rtype: two-tuple of (:class:`requests.Response`, ``Boolean``)
        """
        cached_headers = self.get_headers(url)
        headers = {}
        if not force:
            if 'last-modified' in cached_headers:
                headers['If-Modified-Since'] = cached_headers['last-modified']
            if 'etag' in cached_headers:
                headers['If-None-Match'] = cached_headers['etag']
        else:
            # Ask all possible intermediate proxies to return a fresh response
            headers['Cache-Control'] = 'no-cache'

        verify = settings.DISTRO_TRACKER_CA_BUNDLE or True
        response = requests.get(url, headers=headers, verify=verify,
                                allow_redirects=True)

        # Invalidate previously cached value if the response is not valid now
        if not response.ok:
            if invalidate_cache:
                self.remove(url)
        elif response.status_code == 200:
            # Dump the content and headers only if a new response is generated
            with open(self._content_cache_file_path(url), 'wb') as content_file:
                content_file.write(response.content)
            with open(self._header_cache_file_path(url), 'w') as header_file:
                json.dump(dict(response.headers), header_file)

        return response, response.status_code != 304

    def _prepare_path(self, cache_path):
        path = self.cache_directory_path
        dirname = os.path.dirname(cache_path)

        # Check the directory tree, create missing directories
        check_dir = path
        for component in dirname.split(os.path.sep):
            check_dir = os.path.join(check_dir, component)
            if os.path.isdir(check_dir):
                continue  # Expected case, avoid further checks
            elif os.path.exists(check_dir):
                # Handle conflicting file by renaming it
                target_directory = '{}?'.format(check_dir)
                if not os.path.exists(target_directory):
                    os.mkdir(target_directory)
                os.rename(check_dir, os.path.join(target_directory, 'index'))
                # Also rename the associated headers file if possible
                headers_file = check_dir + '?headers'
                if os.path.exists(headers_file):
                    os.rename(headers_file,
                              os.path.join(target_directory, 'index?headers'))
            os.mkdir(check_dir)

        return os.path.join(self.cache_directory_path, cache_path)

    def _content_cache_file_path(self, url):
        path = self._prepare_path(self.url_to_cache_path(url))
        return path

    def _header_cache_file_path(self, url):
        header_cache_path = self.url_to_cache_path(url) + '?headers'
        path = self._prepare_path(header_cache_path)
        return path

    def url_to_cache_path(self, url):
        """
        Transforms an arbitrary URL into a relative path within the
        cache directory. Can be overridden by the user by supplying
        its own implementation in the ``url_to_cache_path`` attribute
        of the ``__init__()`` method.

        :param url: The URL to be cached.
        :type url: str

        :returns: A relative path within the cache directory, used to store a
            copy of the resource.
        """
        # Let the user supply its own naming logic
        if self.custom_url_to_cache_path:
            return self.custom_url_to_cache_path(url)

        # Normalizes URL into a sane path
        path = re.sub(r'^https?://', '', url, count=1, flags=re.IGNORECASE)
        path = re.sub(r'\?$', '', path)
        path = re.sub(r'/+', '/', path)
        path = re.sub(r'/+$', '', path)

        # Handle URL with GET parameters to allow caching of multiple versions
        # of the same path
        if '?' in path:
            (url, args) = path.split('?', maxsplit=1)
            path = url + '?/' + md5(args.encode('utf-8')).hexdigest()

        # Hande conflicting directory that will forbid save of the cache file
        if os.path.isdir(os.path.join(self.cache_directory_path, path)):
            path += '?/index'

        return path


def get_resource_content(url, cache=None, compression="auto",
                         only_if_updated=False, force_update=False,
                         ignore_network_failures=False,
                         ignore_http_error=None):
    """
    A helper function which returns the content of the resource found at the
    given URL.

    If the resource is already cached in the ``cache`` object and the cached
    content has not expired, the function will not do any HTTP requests and
    will return the cached content.

    If the resource is stale or not cached at all, it is from the Web.

    If the HTTP request returned an error code, the requests module will
    raise a :class:`requests.exceptions.HTTPError`.

    In case of network failures, some `IOError` exception will be raised unless
    `ignore_network_failures` is set to True.

    :param str url: The URL of the resource to be retrieved
    :param cache: A cache object which should be used to look up and store
        the cached resource. If it is not provided, an instance of
        :class:`HttpCache` with a
        ``DISTRO_TRACKER_CACHE_DIRECTORY`` cache directory
        is used.
    :type cache: :class:`HttpCache` or an object with an equivalent interface
    :param str compression: Specifies the compression method used to generate
        the resource, and thus the compression method one should use to
        decompress it. If auto, then guess it from the url file extension.
    :param bool only_if_updated: if set to `True` returns None when no update
        is done. Otherwise, returns the content in any case.
    :param bool force_update: if set to `True` do a new HTTP request even if we
        non-expired data in the cache.
    :param bool ignore_network_failures: if set to `True`, then the function
        will return `None` in case of network failures and not raise any
        exception.
    :param int ignore_http_error: if the request results in an HTTP error
        with the given status code, then the error is ignored and no exception
        is raised. And `None` is returned.

    :returns: The bytes representation of the resource found at the given url
    :rtype: bytes
    """
    if cache is None:
        cache_directory_path = settings.DISTRO_TRACKER_CACHE_DIRECTORY
        cache = HttpCache(cache_directory_path)

    updated = False
    if force_update or cache.is_expired(url):
        try:
            response, updated = cache.update(url, force=force_update)
        except IOError:
            if ignore_network_failures:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning("Failed to update cache with data from %s",
                               url, exc_info=1)
                return
            else:
                raise

    if updated:
        # Check HTTP return code
        if ignore_http_error and response.status_code == ignore_http_error:
            return
        response.raise_for_status()
    else:  # not updated
        if only_if_updated:
            return  # Stop without returning old data

    return cache.get_content(url, compression=compression)


def get_resource_text(*args, **kwargs):
    """
    Clone of :py:func:`get_resource_content` which transparently decodes
    the downloaded content into text. It supports the same parameters
    and adds the encoding parameter.

    :param encoding: Specifies an encoding to decode the resource content.
    :type encoding: str

    :returns: The textual representation of the resource found at the given url.
    :rtype: str
    """

    encoding = kwargs.pop('encoding', 'utf-8')
    content = get_resource_content(*args, **kwargs)

    if content is not None:
        return content.decode(encoding)


def safe_redirect(to, fallback, allowed_hosts=None):
    """Implements a safe redirection to `to` provided that it's safe. Else,
    goes to `fallback`. `allowed_hosts` describes the list of valid hosts for
    the call to :func:`django.utils.http.url_has_allowed_host_and_scheme`.

    :param to: The URL that one should be returned to.
    :type to: str or None

    :param fallback: A safe URL to fall back on if `to` isn't safe. WARNING!
      This url is NOT checked! The developer is advised to put only an url he
      knows to be safe!
    :type fallback: str

    :param allowed_hosts: A list of "safe" hosts. If `None`, relies on the
      default behaviour of
      :func:`django.utils.http.url_has_allowed_host_and_scheme`.
    :type allowed_hosts: list of str

    :returns: A ResponseRedirect instance containing the appropriate intel for
      the redirection.
    :rtype: :class:`django.http.HttpResponseRedirectBase`

    """

    if to and url_has_allowed_host_and_scheme(to, allowed_hosts=allowed_hosts):
        return redirect(to)
    return redirect(fallback)
