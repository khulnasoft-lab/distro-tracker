# -*- coding: utf-8 -*-

# Copyright 2014-2021 The Distro Tracker Developers
# See the COPYRIGHT file at the top-level directory of this distribution and
# at https://deb.li/DTAuthors
#
# This file is part of Distro Tracker. It is subject to the license terms
# in the LICENSE file found in the top-level directory of this
# distribution and at https://deb.li/DTLicense. No part of Distro Tracker,
# including this file, may be copied, modified, propagated, or distributed
# except according to the terms contained in the LICENSE file.

"""
Distro Tracker test infrastructure.
"""

import gzip
import hashlib
import inspect
import io
import json
import lzma
import os
import os.path
import re
import shutil
import tempfile

from bs4 import BeautifulSoup as soup

import django.test
from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test.signals import setting_changed

import responses

from distro_tracker.accounts.models import UserEmail
from distro_tracker.core.models import (
    Architecture,
    BinaryPackageName,
    ContributorName,
    PackageData,
    PackageName,
    Repository,
    SourcePackage,
    SourcePackageName,
)
from distro_tracker.core.utils.compression import (
    get_compressor_factory,
    guess_compression_method,
)
from distro_tracker.core.utils.packages import package_hashdir

from django_email_accounts.models import User


class TempDirsMixin(object):
    """
    Diverts all distro-tracker path settings to make them point
    to temporary directories while testing.
    """

    DISTRO_TRACKER_PATH_SETTINGS = {
        'STATIC_ROOT': 'static',
        'MEDIA_ROOT': 'media',
        'DISTRO_TRACKER_CACHE_DIRECTORY': 'cache',
        'DISTRO_TRACKER_KEYRING_DIRECTORY': 'keyring',
        'DISTRO_TRACKER_TEMPLATE_DIRECTORY': 'templates',
        'DISTRO_TRACKER_LOG_DIRECTORY': 'logs',
        'DISTRO_TRACKER_MAILDIR_DIRECTORY': 'maildir',
    }

    def _backup_settings(self, name):
        self._settings_copy[name] = getattr(settings, name)

    def _restore_settings(self):
        for key, value in self._settings_copy.items():
            setattr(settings, key, value)
            setting_changed.send(sender=self.__class__, setting=key,
                                 value=value, enter=False)

    def __call__(self, result=None):
        """
        Wrapper around __call__ to perform temporary directories setup.
        This means that user-defined Test Cases aren't required to
        include a call to super().setUp().
        """
        self._settings_copy = {}
        self.addCleanup(self._restore_settings)
        self._backup_settings('DISTRO_TRACKER_DATA_PATH')
        tempdir = tempfile.mkdtemp(prefix='distro-tracker-tests-')
        self.addCleanup(shutil.rmtree, tempdir, ignore_errors=True)
        setattr(settings, 'DISTRO_TRACKER_DATA_PATH', tempdir)
        for name, dirname in self.DISTRO_TRACKER_PATH_SETTINGS.items():
            self._backup_settings(name)
            dirname = os.path.join(tempdir, dirname)
            setattr(settings, name, dirname)
            os.mkdir(dirname)
            setting_changed.send(sender=self.__class__, setting=name,
                                 value=dirname, enter=True)

        return super(TempDirsMixin, self).__call__(result)


class TestCaseHelpersMixin(object):
    """
    Helpers method injected into distro_tracker's ``*TestCase`` objects.
    """

    def get_test_data_path(self, name):
        """
        Returns an absolute path name of file within the tests-data
        subdirectory in the calling TestCase.
        """
        return os.path.join(os.path.dirname(inspect.getabsfile(self.__class__)),
                            'tests-data', name)

    def add_test_template_dir(self, name='tests-templates'):
        template_dir = self.get_test_data_path(name)
        settings.TEMPLATES[0]['DIRS'].append(template_dir)
        setting_changed.send(sender=self.__class__, setting='TEMPLATES',
                             value=settings.TEMPLATES, enter=True)

        def cleanup_test_template_dir():
            settings.TEMPLATES[0]['DIRS'].remove(template_dir)
            setting_changed.send(sender=self.__class__, setting='TEMPLATES',
                                 value=settings.TEMPLATES, enter=False)

        self.addCleanup(cleanup_test_template_dir)

    def get_temporary_directory(self, prefix=None, suffix=None):
        tempdir = tempfile.mkdtemp(prefix=prefix, suffix=suffix)
        self.addCleanup(shutil.rmtree, tempdir, ignore_errors=True)

        return tempdir

    def mock_http_request(self, **kwargs):
        responses.start()
        self.addCleanup(responses.stop)
        self.addCleanup(responses.reset)

        if kwargs:
            self.set_http_response(**kwargs)

    @staticmethod
    def compress(data, compression='gzip'):
        if compression == 'gzip':
            return gzip.compress(data)
        elif compression == 'xz':
            return lzma.compress(data)
        else:
            raise NotImplementedError(
                'compress() does not support {} as '
                'compression method'.format(compression))

    def set_http_response(self, url=None, method="GET", body=None, headers=None,
                          status_code=200, json_data=None, compress_with=None):
        # Default URL is the catch-all pattern
        if url is None:
            url = re.compile(".*")

        if headers is None:
            headers = {}

        if compress_with:
            if json_data is not None:
                body = self.compress(
                    json.dumps(json_data).encode('utf-8'),
                    compress_with,
                )
                # Don't forward parameter
                json_data = None
            elif body is not None:
                if isinstance(body, str):
                    body = self.compress(body.encode("utf-8"), compress_with)
                else:
                    body = self.compress(body, compress_with)

        if body is None:
            body = ""

        responses.remove(method, url)
        responses.add(
            method=method,
            url=url,
            body=body,
            json=json_data,
            status=status_code,
            headers=headers,
        )

    def import_key_into_keyring(self, filename):
        """
        Imports a key from an ascii armored file located in tests-data/keys/
        into Distro Tracker's keyrings/.
        """
        import gpg

        old = os.environ.get('GNUPGHOME', None)
        os.environ['GNUPGHOME'] = settings.DISTRO_TRACKER_KEYRING_DIRECTORY

        file_path = self.get_test_data_path('keys/' + filename)
        keydata = gpg.Data()
        keydata.new_from_file(file_path)

        with gpg.Context() as ctx:
            ctx.op_import(keydata)

        if old:
            os.environ['GNUPGHOME'] = old


class DatabaseMixin(object):
    """
    Database-related assertions injected into distro_tracker's ``*TestCase``
    objects.
    """

    def assertDoesNotExist(self, obj):
        with self.assertRaises(obj.__class__.DoesNotExist):
            obj.__class__.objects.get(pk=obj.id)

    def assertDoesExist(self, obj):
        try:
            self.assertIsNotNone(obj.__class__.objects.get(pk=obj.id))
        except obj.__class__.DoesNotExist as error:
            raise AssertionError(error)

    def create_source_package(self, **kwargs):
        """
        Creates a source package and any related object requested through the
        keyword arguments. The following arguments are supported:
        - name
        - version
        - directory
        - dsc_file_name
        - maintainer (dict with 'name' and 'email')
        - uploaders (list of emails)
        - architectures (list of architectures)
        - binary_packages (list of package names)
        - repository (shorthand of a repository)
        - repositories (list of repositories' shorthand)
        - data (dict used to generate associated PackageData)

        If the shorthand of the requested repository is 'default', then
        its default field will be set to True.

        :return: the created source package
        :rtype: :class:`~distro_tracker.core.models.SourcePackage`
        """
        name = kwargs.get('name', 'test-package')
        version = kwargs.get('version', '1')

        fields = {}
        fields['source_package_name'] = \
            SourcePackageName.objects.get_or_create(name=name)[0]
        fields['version'] = version
        fields['dsc_file_name'] = kwargs.get('dsc_file_name',
                                             '%s_%s.dsc' % (name, version))
        fields['directory'] = kwargs.get(
            'directory', 'pool/main/%s/%s' % (package_hashdir(name), name))

        if 'maintainer' in kwargs:
            maintainer = kwargs['maintainer']
            maintainer_email = UserEmail.objects.get_or_create(
                email=maintainer['email'])[0]
            fields['maintainer'] = ContributorName.objects.get_or_create(
                contributor_email=maintainer_email,
                name=maintainer.get('name', ''))[0]

        srcpkg = SourcePackage.objects.create(**fields)

        for architecture in kwargs.get('architectures', []):
            srcpkg.architectures.add(
                Architecture.objects.get_or_create(name=architecture)[0])

        for uploader in kwargs.get('uploaders', []):
            contributor = ContributorName.objects.get_or_create(
                contributor_email=UserEmail.objects.get_or_create(
                    email=uploader)[0])[0]
            srcpkg.uploaders.add(contributor)

        for binary in kwargs.get('binary_packages', []):
            srcpkg.binary_packages.add(
                BinaryPackageName.objects.get_or_create(name=binary)[0])

        if 'repository' in kwargs:
            kwargs.setdefault('repositories', [kwargs['repository']])
        for repo_shorthand in kwargs.get('repositories', []):
            self.add_to_repository(srcpkg, repo_shorthand)

        if 'data' in kwargs:
            self.add_package_data(srcpkg.source_package_name, **kwargs['data'])

        srcpkg.save()
        return srcpkg

    def add_to_repository(self, srcpkg, shorthand='default'):
        """
        Add a source package to a repository. Creates the repository if it
        doesn't exist.

        If the shorthand of the requested repository is 'default', then
        its default field will be set to True.

        :param srcpkg: the source package to add to the repository
        :type srcpkg: :class:`~distro_tracker.core.models.SourcePackage`
        :param str shorthand: the shorthand of the repository

        :return: the repository entry that has been created
        :rtype:
            :class:`~distro_tracker.core.models.SourcePackageRepositoryEntry`
        """
        repository, _ = Repository.objects.get_or_create(
            shorthand=shorthand,
            defaults={
                'name': 'Test repository %s' % shorthand,
                'uri': 'http://localhost/debian',
                'suite': shorthand,
                'codename': shorthand,
                'components': ['main', 'contrib', 'non-free'],
                'default': True if shorthand == 'default' else False,
            }
        )
        return srcpkg.repository_entries.create(repository=repository,
                                                component='main')

    def remove_from_repository(self, srcpkg, shorthand='default'):
        """
        Remove a source package from a repository.

        :param srcpkg: the source package to add to the repository
        :type srcpkg: :class:`~distro_tracker.core.models.SourcePackage`
        :param str shorthand: the shorthand of the repository
        """
        return srcpkg.repository_entries.filter(
            repository__shorthand=shorthand).delete()[0]

    def add_package_data(self, pkgname, **kwargs):
        """
        Creates PackageData objects associated to the package indicated
        in pkgname. Each named parameter results in PackageData instance
        with the `key` being the name of the parameter and the `value`
        being the value of the named parameter.

        :param pkgname: the name of the package to which we want to associate
            data
        :type pkgname: `str` or :class:`~distro_tracker.core.models.PackageName`
        """
        if not isinstance(pkgname, PackageName):
            pkgname, _ = PackageName.objects.get_or_create(name=str(pkgname))
        for key, value in kwargs.items():
            PackageData.objects.create(package=pkgname, key=key, value=value)

    @staticmethod
    def create_repository(
        codename="sid",
        name=None,
        shorthand=None,
        uri="http://localhost/debian",
        suite=None,
        components="main contrib non-free",
        default=False,
        optional=True,
        binary=False,
        source=True,
        architectures=None,
    ):
        if not name:
            name = "Repository %s" % codename
        if not shorthand:
            shorthand = codename[:10]
        if not suite:
            suite = codename

        repo = Repository.objects.create(
            name=name,
            shorthand=shorthand,
            uri=uri,
            public_uri=uri,
            codename=codename,
            suite=suite,
            components=components,
            default=default,
            optional=optional,
            binary=binary,
            source=source,
        )

        if not architectures:
            architectures = ["amd64", "i386"]
        for archname in architectures:
            arch, _ = Architecture.objects.get_or_create(name=archname)
            repo.architectures.add(arch)

        return repo


class SimpleTestCase(TempDirsMixin, TestCaseHelpersMixin,
                     django.test.SimpleTestCase):
    pass


class TestCase(TempDirsMixin, TestCaseHelpersMixin, DatabaseMixin,
               django.test.TestCase):
    pass


@django.test.tag('transaction')
class TransactionTestCase(TempDirsMixin, TestCaseHelpersMixin,
                          DatabaseMixin, django.test.TransactionTestCase):
    pass


class LiveServerTestCase(TempDirsMixin, TestCaseHelpersMixin,
                         DatabaseMixin, StaticLiveServerTestCase):
    pass


class TemplateTestsMixin(object):
    """Helper methods to tests templates"""

    @staticmethod
    def html_contains_link(text, link):
        html = soup(text, 'html.parser')
        for a_tag in html.findAll('a', {'href': True}):
            if a_tag['href'] == link:
                return True
        return False

    def assertLinkIsInResponse(self, response, link):
        self.assertTrue(self.html_contains_link(response.content, link))

    def assertLinkIsNotInResponse(self, response, link):
        self.assertFalse(self.html_contains_link(response.content, link))


class UserAuthMixin(object):
    """
    Helpers methods to manage user authentication.
    One may define additional USERS before call self.setup_users()
    in self.setUp()
    """
    USERS = {
        'john': {},
    }

    def setup_users(self, login=False):
        """
        Creates users defined in self.USERS and use the 'login' parameter as
        follows:
        * If False: no user login
        * If True: login with the only user defined
        * If a particular username: login with the user who owns the username
        """
        self.users = {}
        for username in self.USERS:
            user_data = self._get_user_data(username)
            self.users[username] = User.objects.create_user(**user_data)
        if login:
            username = None if login is True else login
            self.login(username)

    def login(self, username=None):
        """
        Login with the user that owns the 'username' or with the only available
        user in self.users. If multiple users are available, you must specify
        the username or you will trigger a ValueError exception.
        """
        if not username:
            if len(self.users) > 1:
                raise ValueError("multiple users but username not specified")
            username = list(self.users.keys())[0]
        user_data = self._get_user_data(username)
        self.client.login(
            username=user_data['main_email'],
            password=user_data['password'],
        )
        self.current_user = self.users[username]
        return self.current_user

    def get_user(self, username=None):
        if not username:
            return self.current_user
        return self.users[username]

    def _get_user_data(self, username):
        user_data = self.USERS[username].copy()
        user_data.setdefault('main_email', '{}@example.com'.format(username))
        user_data.setdefault('password', '{}password'.format(username))
        return user_data


class AptRepositoryMixin(object):
    """
    Helper method to mock an APT repository.
    """

    def mock_apt_repository(self, repo, **kwargs):
        self.mock_http_request()
        global_compression_suffixes = kwargs.pop("compression_suffixes", [""])
        global_content = kwargs.pop("content", None)
        # Mock Sources and Packages files
        for base_filename in self._apt_repo_iter_metadata(repo):
            metadata_options = kwargs.get("metadata_options", {}).get(
                base_filename, {}
            )
            compression_suffixes = metadata_options.get(
                "compression_suffixes", global_compression_suffixes
            )
            metadata_content = metadata_options.get("content", global_content)
            test_content_file = metadata_options.get("test_content_file")
            for suffix in ("", ".bz2", ".gz", ".xz"):
                filename = base_filename + suffix
                content = metadata_content
                if callable(metadata_content):
                    content = metadata_content(repo, filename)
                if suffix in compression_suffixes:
                    self.mock_apt_repository_add_metadata_file(
                        repo,
                        filename,
                        content=content,
                        test_content_file=test_content_file,
                    )
                else:
                    url = self._apt_repo_build_url(repo, filename)
                    self.set_http_response(url, status_code=404)
        # Mock Release/InRelease files
        self.mock_apt_repository_update_release_file(repo, **kwargs)

    @staticmethod
    def _apt_repo_build_url(repo, filename):
        return "{}/dists/{}/{}".format(repo.uri, repo.codename, filename)

    @staticmethod
    def _apt_repo_iter_metadata(repo):
        for component in sorted(repo.components.split()):
            for arch in repo.architectures.all().order_by('name'):
                yield f"{component}/binary-{arch.name}/Packages"
            yield f"{component}/source/Sources"

    def _apt_repo_init_checksums(self, repo):
        if not hasattr(self, '_apt_repo_checksums'):
            self._apt_repo_checksums = {}
        self._apt_repo_checksums.setdefault(repo.shorthand, {})

    def _apt_repo_iter_checksums(self, repo):
        return self._apt_repo_checksums[repo.shorthand].items()

    def _apt_repo_store_checksums(self, repo, filename, checksums):
        self._apt_repo_checksums[repo.shorthand][filename] = checksums

    def mock_apt_repository_add_metadata_file(
        self, repo, filename, content=None, test_content_file=None,
        compression="auto", **kwargs,
    ):
        self._apt_repo_init_checksums(repo)

        # Load test content if required
        if test_content_file:
            data_path = self.get_test_data_path(test_content_file)
            with open(data_path, 'rb') as f:
                content = f.read()

        # Generate content if required, then compress it if required
        if content is None:
            content = b""

        # Detect compression method
        if compression == "auto":
            compression = guess_compression_method(filename)

        if compression:
            stream = io.BytesIO()
            compressor = get_compressor_factory(compression)(stream, mode="wb")
            compressor.write(content)
            compressor.close()
            content = stream.getvalue()

        # Store checksums of metadata
        checksums = {
            "Size": len(content),
            "MD5Sum": hashlib.md5(content).hexdigest(),
            "SHA256": hashlib.sha256(content).hexdigest(),
        }
        self._apt_repo_store_checksums(repo, filename, checksums)

        # Register the metadata in the http mock
        url = self._apt_repo_build_url(repo, filename)
        self.set_http_response(url, body=content)

    def mock_apt_repository_update_release_file(
        self,
        repo,
        enable_inrelease=True,
        acquire_by_hash=True,
        suite=None,
        codename=None,
        architectures=None,
        components=None,
        **kwargs,
    ):
        self._apt_repo_init_checksums(repo)

        release_url = self._apt_repo_build_url(repo, "Release")
        inrelease_url = self._apt_repo_build_url(repo, "InRelease")
        if suite is None:
            suite = repo.suite or repo.codename or ""
        if codename is None:
            codename = repo.codename or repo.suite or ""
        if architectures is None:
            architectures = " ".join([
                a.name for a in repo.architectures.all().order_by('name')
            ])
        if components is None:
            components = repo.components

        # Build the content of the release file
        text = """Origin: Debian
Label: Debian
Suite: {suite}
Codename: {codename}
Architectures: {architectures}
Components: {components}
""".format(
            suite=suite,
            codename=codename,
            architectures=architectures,
            components=components,
        )
        if acquire_by_hash:
            text += "Acquire-By-Hash: yes\n"
        for checksum in ("MD5Sum", "SHA256"):
            text += "{}:\n".format(checksum)
            for path, checksums in self._apt_repo_iter_checksums(repo):
                if "/by-hash/" in path:
                    continue
                text += " {} {} {}\n".format(
                    checksums[checksum], checksums["Size"], path
                )

        self.set_http_response(release_url, body=text)

        if enable_inrelease:
            signed_text = """-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA256

"""
            signed_text += text
            signed_text += """-----BEGIN PGP SIGNATURE-----

iQIzBAEBCAAdFiEEFukLP99l7eOqfzI8BO5yN7fUU+wFAl8/gbEACgkQBO5yN7fU
U+y4Lw/+PDhJJaxEmZWS4dFjBSJYMTgyiEPXG6eMqDpeJNr8iIoBjcBd3bv3Gexq
8rS0ry9bPLy9ZZxImL0E6rB2oFU8OAqoAXXmRf5yt3x0SY/1deTjMHYr5w4kH6CB
ZwZnkm12jMyB9ds/ZAvG7+ou+qEb7bZ2+7IzhBlFuLNYO747sOaDjOM3RdV700qs
FvmSBcysOUWCAhxQNmAk/NZ585AxeKksbvSHUMczdKIRu/XN82zrTRPQhZ51eHDZ
mY444ytopHEA6G+3rkUagKeLGE6JnwS+amhz/A==
=H/pA
-----END PGP SIGNATURE-----"""
            self.set_http_response(inrelease_url, body=signed_text)
        else:
            self.set_http_response(inrelease_url, status_code=404)
