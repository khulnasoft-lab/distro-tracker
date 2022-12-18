# -*- coding: utf-8 -*-

# Copyright 2013-2020 The Distro Tracker Developers
# See the COPYRIGHT file at the top-level directory of this distribution and
# at https://deb.li/DTAuthors
#
# This file is part of Distro Tracker. It is subject to the license terms
# in the LICENSE file found in the top-level directory of this
# distribution and at https://deb.li/DTLicense. No part of Distro Tracker,
# including this file, may be copied, modified, propagated, or distributed
# except according to the terms contained in the LICENSE file.
"""
Tests for the :mod:`distro_tracker.extract_source_files` app.
"""

import itertools
import os
from pathlib import Path
from unittest import mock

from django.core.files.base import ContentFile

from distro_tracker.core.models import ExtractedSourceFile
from distro_tracker.extract_source_files.tracker_tasks import (
    ExtractSourcePackageFiles
)
from distro_tracker.test import TestCase


@mock.patch('distro_tracker.extract_source_files.tracker_tasks.'
            'AptCache.retrieve_source')
class ExtractSourcePackageFilesTest(TestCase):
    """
    Tests for the task
    :class:`distro_tracker.extract_source_files.ExtractSourcePackageFiles`.
    """
    def setUp(self):
        self.task = ExtractSourcePackageFiles()
        self.srcpkg = self.create_source_package()
        self.pkg_directory = self.get_temporary_directory(
            prefix='dtracker-pkg-dir-')

    def run_task(self, force_update=False):
        """
        Initiates the task run.

        :param bool force_update: force a full run
        """
        if force_update:
            self.task.initialize(force_update=True)
        self.task.execute()

    def setup_debian_dir(self, pkg_directory, files_to_create=None,
                         extra_files=[], contents=b'Contents'):
        debian_dir = os.path.join(pkg_directory, 'debian')
        os.makedirs(debian_dir)
        if files_to_create is None:
            files_to_create = self.task.ALL_FILES_TO_EXTRACT

        for file_name in itertools.chain(files_to_create, extra_files):
            file_path = os.path.join(debian_dir, file_name)
            with open(file_path, 'wb') as f:
                f.write(contents)

        return debian_dir

    def assertExtractedFilesInDB(self, expected=None):
        if expected is None:
            expected = self.task.ALL_FILES_TO_EXTRACT
        expected = set(expected)
        extracted = set([
            x.name for x in self.srcpkg.extracted_source_files.all()
        ])
        self.assertSetEqual(expected, extracted)

    def test_create_extracted_files(self, mock_cache):
        """
        Tests that the task creates an
        :class:`distro_tracker.core.models.ExtractedSourceFile` instance.
        """
        mock_cache.return_value = self.pkg_directory
        self.setup_debian_dir(self.pkg_directory, ['changelog'])
        self.run_task()

        self.assertExtractedFilesInDB(['changelog'])

    def test_create_extracted_files_only_wanted_files(self, mock_cache):
        """
        Tests that the task creates an
        :class:`distro_tracker.core.models.ExtractedSourceFile` instance.
        """
        mock_cache.return_value = self.pkg_directory
        self.setup_debian_dir(self.pkg_directory, extra_files=['other-file'])
        self.run_task()

        self.assertExtractedFilesInDB()

    def test_create_extracted_files_with_non_utf8_content(self, mock_cache):
        """
        Tests that the task creates an
        :class:`distro_tracker.core.models.ExtractedSourceFile` instance
        even when the content of the file is not valid UTF-8.
        """
        mock_cache.return_value = self.pkg_directory
        self.setup_debian_dir(self.pkg_directory, ['changelog'],
                              contents='Raphaël'.encode('latin1'))
        self.run_task()

        self.assertExtractedFilesInDB(['changelog'])

    def test_task_force_update_no_existing_files(self, mock_cache):
        """
        Test that the force_update mode extracts missing files for already
        processed source packages.
        """
        self.task.item_mark_processed(self.srcpkg)

        mock_cache.return_value = self.pkg_directory
        self.setup_debian_dir(self.pkg_directory)
        self.run_task(force_update=True)

        self.assertExtractedFilesInDB()

    def test_task_with_existing_files(self, mock_cache):
        """
        Ensure task doesn't overwrite existing files when it re-process
        a package that was already processed.
        """
        # Make a previously extracted file.
        original_content = b'Original content'
        self.srcpkg.extracted_source_files.create(
            name='changelog',
            extracted_file=ContentFile(original_content, name='changelog'))

        mock_cache.return_value = self.pkg_directory
        self.setup_debian_dir(self.pkg_directory)
        self.run_task()

        self.assertExtractedFilesInDB()

        # Check that the existing file was not changed.
        extracted_file = ExtractedSourceFile.objects.get(
            name='changelog', source_package=self.srcpkg)
        extracted_file.extracted_file.open()
        content = extracted_file.extracted_file.read()
        extracted_file.extracted_file.close()
        self.assertEqual(original_content, content)

    def test_task_remove_unwanted_file(self, mock_cache):
        # Make a previously extracted file that we no longer extract
        original_content = 'Original content'
        ExtractedSourceFile.objects.create(
            source_package=self.srcpkg,
            name='we-dont-want-this-any-more',
            extracted_file=ContentFile(original_content, name='changelog'))

        mock_cache.return_value = self.pkg_directory
        self.setup_debian_dir(self.pkg_directory)
        self.run_task()

        self.assertExtractedFilesInDB()

    def test_task_removes_outdated_files(self, mock_cache):
        """The task removes outdated files but keep current files."""
        # Make a previously extracted file.
        original_content = b'Original content'
        extracted_file = self.srcpkg.extracted_source_files.create(
            name='changelog',
            extracted_file=ContentFile(original_content, name='changelog'))
        current_path = Path(extracted_file.extracted_file.path)

        # Create a similar file not tied to any ExtractedSourceFile
        new_path = current_path.with_name('changelog-1.2.3')
        with open(new_path, 'w') as f:
            f.write('New file')

        # Create another file not matching one of the extracted file
        unrelated_path = current_path.with_name('somethingunrelated-1.2.3')
        with open(unrelated_path, 'w') as f:
            f.write('Unrelated file')

        # All the files are here
        self.assertTrue(new_path.exists())
        self.assertTrue(current_path.exists())
        self.assertTrue(unrelated_path.exists())

        self.run_task()

        # Only the file without association is gone
        self.assertTrue(current_path.exists())
        self.assertTrue(unrelated_path.exists())
        self.assertFalse(new_path.exists())
