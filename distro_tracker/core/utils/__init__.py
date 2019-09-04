# Copyright 2013-2019 The Distro Tracker Developers
# See the COPYRIGHT file at the top-level directory of this distribution and
# at https://deb.li/DTAuthors
#
# This file is part of Distro Tracker. It is subject to the license terms
# in the LICENSE file found in the top-level directory of this
# distribution and at https://deb.li/DTLicense. No part of Distro Tracker,
# including this file, may be copied, modified, propagated, or distributed
# except according to the terms contained in the LICENSE file.
"""Various utilities for the distro-tracker project."""
import datetime
import json
import logging
import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.db import models
from django.http import HttpResponse
from django.template.loader import render_to_string

import gpg

from distro_tracker import vendor

# Re-export some functions
from .email_messages import extract_email_address_from_header  # noqa
from .email_messages import get_decoded_message_payload        # noqa
from .email_messages import message_from_bytes                 # noqa

logger_input = logging.getLogger('distro_tracker.input')


def get_or_none(model, **kwargs):
    """
    Gets a Django Model object from the database or returns ``None`` if it
    does not exist.
    """
    try:
        return model.objects.get(**kwargs)
    except model.DoesNotExist:
        return None


def distro_tracker_render_to_string(template_name, context=None):
    """
    A custom function to render a template to a string which injects extra
    distro-tracker specific information to the context, such as the name
    of the derivative.

    This function is necessary since Django's
    :data:`TEMPLATE_CONTEXT_PROCESSORS
    <distro_tracker.project.settings.TEMPLATE_CONTEXT_PROCESSORS> only work when
    using a :class:`RequestContext <django.template.RequestContext>`, whereas
    this function can be called independently from any HTTP request.
    """
    from distro_tracker.core import context_processors
    if context is None:
        context = {}
    extra_context = context_processors.DISTRO_TRACKER_EXTRAS
    context.update(extra_context)

    return render_to_string(template_name, context)


def render_to_json_response(response):
    """
    Helper function creating an :class:`HttpResponse <django.http.HttpResponse>`
    by serializing the given ``response`` object to a JSON string.

    The resulting HTTP response has Content-Type set to application/json.

    :param response: The object to be serialized in the response. It must be
        serializable by the :mod:`json` module.
    :rtype: :class:`HttpResponse <django.http.HttpResponse>`
    """
    return HttpResponse(
        json.dumps(response),
        content_type='application/json'
    )


class PrettyPrintList(object):
    """
    A class which wraps the built-in :class:`list` object so that when it is
    converted to a string, its contents are printed using the given
    :attr:`delimiter`.

    The default delimiter is a space.

    >>> a = PrettyPrintList([1, 2, 3])
    >>> print(a)
    1 2 3
    >>> print(PrettyPrintList([u'one', u'2', u'3']))
    one 2 3
    >>> print(PrettyPrintList([1, 2, 3], delimiter=', '))
    1, 2, 3
    >>> # Still acts as a list
    >>> a == [1, 2, 3]
    True
    >>> a == ['1', '2', '3']
    False
    """
    def __init__(self, the_list=None, delimiter=' '):
        if the_list is None:
            self._list = []
        else:
            self._list = the_list
        self.delimiter = delimiter

    def __getattr__(self, name, *args, **kwargs):
        return getattr(self._list, name)

    def __len__(self):
        return len(self._list)

    def __getitem__(self, pos):
        return self._list[pos]

    def __iter__(self):
        return self._list.__iter__()

    def __str__(self):
        return self.delimiter.join(map(str, self._list))

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        if isinstance(other, PrettyPrintList):
            return self._list == other._list
        return self._list == other


class SpaceDelimitedTextField(models.TextField):
    """
    A custom Django model field which stores a list of strings.

    It stores the list in a :class:`TextField <django.db.models.TextField>` as a
    space delimited list. It is marshalled back to a :class:`PrettyPrintList` in
    the Python domain.
    """

    description = "Stores a space delimited list of strings"

    def from_db_value(self, value, expression, connection, context):
        return self.to_python(value)

    def to_python(self, value):
        if value is None:
            return None

        if isinstance(value, PrettyPrintList):
            return value
        elif isinstance(value, list):
            return PrettyPrintList(value)

        return PrettyPrintList(value.split())

    def get_prep_value(self, value, **kwargs):
        if value is None:
            return
        # Any iterable value can be converted into this type of field.
        return ' '.join(map(str, value))

    def get_db_prep_value(self, value, **kwargs):
        return self.get_prep_value(value)

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_prep_value(value)


#: A map of currently available VCS systems' shorthands to their names.
VCS_SHORTHAND_TO_NAME = {
    'svn': 'Subversion',
    'git': 'Git',
    'bzr': 'Bazaar',
    'cvs': 'CVS',
    'darcs': 'Darcs',
    'hg': 'Mercurial',
    'mtn': 'Monotone',
}


def get_vcs_name(shorthand):
    """
    Returns a full name for the VCS given its shorthand.

    If the given shorthand is unknown an empty string is returned.

    :param shorthand: The shorthand of a VCS for which a name is required.

    :rtype: string
    """
    return VCS_SHORTHAND_TO_NAME.get(shorthand, shorthand)


def verify_signature(content):
    """
    The function extracts any possible signature information found in the given
    content.

    Uses the ``DISTRO_TRACKER_KEYRING_DIRECTORY`` setting to access the keyring.
    If this setting does not exist, no signatures can be validated.

    :type content: :class:`bytes` or :class:`string`

    :returns: Information about the signers of the content as a list or
        ``None`` if there is no (valid) signature.
    :rtype: list of ``(name, email)`` pairs or ``None``
    :type content: :class:`bytes`
    """
    keyring_directory = getattr(settings, 'DISTRO_TRACKER_KEYRING_DIRECTORY',
                                None)
    if not keyring_directory:
        # The vendor has not provided a keyring
        return None

    if content is None:
        return None

    if isinstance(content, str):
        content = content.encode('utf-8')

    os.environ['GNUPGHOME'] = keyring_directory
    signers = []

    with gpg.Context() as ctx:

        # Try to verify the given content
        signed_data = gpg.Data()
        signed_data.new_from_mem(content)

        try:
            _, result = ctx.verify(signed_data)
        except gpg.errors.BadSignatures:
            return []
        except gpg.errors.GpgError:
            return None

        # Extract signer information
        for signature in result.signatures:
            key_missing = bool(signature.summary &
                               gpg.constants.SIGSUM_KEY_MISSING)

            if key_missing:
                continue

            key = ctx.get_key(signature.fpr)
            preferred_domain = "".join(
                settings.DISTRO_TRACKER_FQDN.split(".", 1)[1:2])

            selected_uid = _select_uid_in_key(key, domain=preferred_domain)
            if not selected_uid:
                selected_uid = _select_uid_in_key(key)

            if selected_uid:
                signers.append((selected_uid.name, selected_uid.email))
            else:
                logger_input.warning(
                    'Key %s has no valid UID (name=%s email=%s)', signature.fpr,
                    key.uids[0].name, key.uids[0].email)

    return signers


def _select_uid_in_key(key, domain=None):
    """
    Select the desired UID among all the available UIDs.
    """
    selected_uid = None
    validate_email = EmailValidator()

    for uid in key.uids:
        if uid.revoked or uid.invalid:
            continue
        try:
            validate_email(uid.email)
            if domain:
                if uid.email.endswith('@' + domain):
                    selected_uid = uid
                    break
            else:
                selected_uid = uid
                break
        except ValidationError:
            continue

    return selected_uid


def now(tz=datetime.timezone.utc):
    """
    Returns the current timestamp in the requested timezone (UTC by default)
    and can be easily mocked out for tests.
    """
    return datetime.datetime.now(tz)


def get_developer_information_url(email):
    """
    Returns developer's information url based on his/her email
    through vendor-specific function
    """
    info_url, implemented = vendor.call(
        'get_developer_information_url', **{'developer_email': email, })
    if implemented and info_url:
        return info_url


def add_developer_extras(general, url_only=False):
    """
    Receives a general dict with package data and add to it more data
    regarding that package's developers
    """
    if 'maintainer' in general:
        maintainer_email = general['maintainer']['email']
        url = get_developer_information_url(maintainer_email)
        if url:
            general['maintainer']['developer_info_url'] = url
            if not url_only:
                extra, implemented = vendor.call(
                    'get_maintainer_extra', maintainer_email, general['name'])
                general['maintainer']['extra'] = extra

    uploaders = general.get('uploaders', None)
    if uploaders:
        for uploader in uploaders:
            url = get_developer_information_url(uploader['email'])
            if url:
                uploader['developer_info_url'] = url
            if url_only:
                continue
            # Vendor specific extras.
            extra, implemented = vendor.call(
                'get_uploader_extra', uploader['email'], general['name'])
            if implemented and extra:
                uploader['extra'] = extra

    return general
