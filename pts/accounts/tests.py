# Copyright 2013 The Debian Package Tracking System Developers
# See the COPYRIGHT file at the top-level directory of this distribution and
# at http://deb.li/ptsauthors
#
# This file is part of the Package Tracking System. It is subject to the
# license terms in the LICENSE file found in the top-level directory of
# this distribution and at http://deb.li/ptslicense. No part of the Package
# Tracking System, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE file.
"""
Tests for the :mod:`pts.accounts` app.
"""
from __future__ import unicode_literals
from django.test import TestCase
from pts.accounts.models import User
from pts.core.models import EmailUser
from pts.core.models import PackageName
from pts.core.models import Subscription
from django.core.urlresolvers import reverse

import json


class UserManagerTests(TestCase):
    """
    Tests for the :class:`pts.accounts.UserManager` class.
    """
    def test_create_user(self):
        email = 'user@domain.com'

        u = User.objects.create_user(main_email=email, password='asdf')

        # The user is correctly created
        self.assertEqual(1, User.objects.count())
        self.assertEqual(email, u.main_email)
        self.assertFalse(u.is_superuser)
        self.assertFalse(u.is_staff)
        self.assertTrue(u.is_active)
        # The user is associated with a EmailUser
        self.assertEqual(1, u.emails.count())
        email_user = EmailUser.objects.all()[0]
        self.assertEqual(u, email_user.user)

    def test_create_user_existing_email(self):
        """
        Tests creating a user when the email already exists.
        """
        email = 'user@domain.com'
        EmailUser.objects.create(email=email)

        u = User.objects.create_user(main_email=email, password='asdf')

        # The user is associated with the existing email user
        self.assertEqual(1, EmailUser.objects.count())
        self.assertEqual(u, EmailUser.objects.all()[0].user)

    def test_create_superuser(self):
        email = 'user@domain.com'

        u = User.objects.create_superuser(main_email=email, password='asdf')

        # The user is created
        self.assertEqual(1, User.objects.count())
        self.assertTrue(u.is_superuser)
        self.assertTrue(u.is_staff)

    def test_create(self):
        email = 'user@domain.com'

        u = User.objects.create(main_email=email, password='asdf')

        # The user is correctly created
        self.assertEqual(1, User.objects.count())
        self.assertEqual(email, u.main_email)
        self.assertFalse(u.is_superuser)
        self.assertFalse(u.is_staff)
        # This creates inactive users
        self.assertFalse(u.is_active)
        # The user is associated with a EmailUser
        self.assertEqual(1, u.emails.count())
        email_user = EmailUser.objects.all()[0]
        self.assertEqual(u, email_user.user)


class UserTests(TestCase):
    """
    Tests for the :class:`pts.accounts.User` class.
    """
    def setUp(self):
        self.user = User.objects.create_user(
            main_email='user@domain.com', password='asdf')
        self.package = PackageName.objects.create(name='dummy-package')

    def test_is_subscribed_to_main_email(self):
        """
        Tests the
        :meth:`is_subscribed_to <pts.accounts.models.User.is_subscribed_to>`
        method when the user is subscribed to the package with his main email
        only.
        """
        email = self.user.emails.all()[0]
        Subscription.objects.create_for(
            email=email.email,
            package_name=self.package.name)

        self.assertTrue(self.user.is_subscribed_to(self.package))
        self.assertTrue(self.user.is_subscribed_to('dummy-package'))

    def test_is_subscribed_to_associated_email(self):
        """
        Tests the
        :meth:`is_subscribed_to <pts.accounts.models.User.is_subscribed_to>`
        method when the user is subscribed to the package with one of his
        associated emails.
        """
        email = self.user.emails.create(email='other-email@domain.com')
        Subscription.objects.create_for(
            email=email.email,
            package_name=self.package.name)

        self.assertTrue(self.user.is_subscribed_to(self.package))
        self.assertTrue(self.user.is_subscribed_to('dummy-package'))

    def test_is_subscribed_to_all_emails(self):
        """
        Tests the
        :meth:`is_subscribed_to <pts.accounts.models.User.is_subscribed_to>`
        method when the user is subscribed to the package with all of his
        associated emails.
        """
        self.user.emails.create(email='other-email@domain.com')
        for email in self.user.emails.all():
            Subscription.objects.create_for(
                email=email.email,
                package_name=self.package.name)

        self.assertTrue(self.user.is_subscribed_to(self.package))
        self.assertTrue(self.user.is_subscribed_to('dummy-package'))


class SubscriptionsViewTests(TestCase):
    """
    Tests the :class:`pts.accounts.SubscriptionsView`.
    """
    def setUp(self):
        self.package_name = PackageName.objects.create(name='dummy-package')

        self.password = 'asdf'
        self.user = User.objects.create_user(
            main_email='user@domain.com',
            password=self.password)

    def get_subscriptions_view(self):
        self.client.login(username=self.user.main_email, password=self.password)
        return self.client.get(reverse('pts-accounts-subscriptions'))

    def subscribe_email_to_package(self, email, package_name):
        Subscription.objects.create_for(
            email=email,
            package_name=package_name.name)

    def test_one_email(self):
        """
        Tests the scenario where the user only has one email associated with
        his account.
        """
        self.subscribe_email_to_package(self.user.main_email, self.package_name)

        response = self.get_subscriptions_view()

        self.assertTemplateUsed(response, 'accounts/subscriptions.html')
        # The context contains the subscriptions of the user
        self.assertIn('subscriptions', response.context)
        context_subscriptions = response.context['subscriptions']
        email = self.user.emails.all()[0]
        # The correct email is in the context
        self.assertIn(email, context_subscriptions)
        # The packages in the context are correct
        self.assertEqual(
            [self.package_name.name],
            [sub.package.name for sub in context_subscriptions[email]])

    def test_multiple_emails(self):
        """
        Tests the scenario where the user has multiple emails associated with
        his account.
        """
        self.user.emails.create(email='other-email@domain.com')
        packages = [
            self.package_name,
            PackageName.objects.create(name='other-package')]
        for email, package in zip(self.user.emails.all(), packages):
            self.subscribe_email_to_package(email.email, package)

        response = self.get_subscriptions_view()

        # All the emails are in the context?
        context_subscriptions = response.context['subscriptions']
        for email, package in zip(self.user.emails.all(), packages):
            self.assertIn(email, context_subscriptions)
            # Each email has the correct package?
            self.assertEqual(
                [package.name],
                [sub.package.name for sub in context_subscriptions[email]])


class UserEmailsViewTests(TestCase):
    """
    Tests for the :class:`pts.accounts.views.UserEmailsView` view.
    """
    def setUp(self):
        self.password = 'asdf'
        self.user = User.objects.create_user(
            main_email='user@domain.com', password=self.password)

    def log_in_user(self):
        self.client.login(username=self.user.main_email, password=self.password)

    def get_emails_view(self):
        return self.client.get(reverse('pts-api-accounts-emails'))

    def test_get_list_of_emails_only_main_email(self):
        self.log_in_user()

        response = self.get_emails_view()

        # The view returns JSON
        self.assertEqual('application/json', response['Content-Type'])
        # The array contains only the users main email
        self.assertEqual(
            [email.email for email in self.user.emails.all()],
            json.loads(response.content))

    def test_user_not_logged_in(self):
        """
        Tests that when a user is not logged in, no JSON response is given.
        """
        response = self.get_emails_view()

        self.assertNotEqual('application/json', response['Content-Type'])

    def test_get_list_of_emails_with_associated_emails(self):
        self.user.emails.create(email='other@domain.com')
        self.log_in_user()

        response = self.get_emails_view()

        # The array contains only the users main email
        self.assertEqual(
            [email.email for email in self.user.emails.all()],
            json.loads(response.content))


class SubscribeUserToPackageViewTests(TestCase):
    """
    Tests for the :class:`pts.accounts.views.SubscribeUserToPackageView` view.
    """
    def setUp(self):
        self.password = 'asdf'
        self.user = User.objects.create_user(
            main_email='user@domain.com', password=self.password)
        self.package = PackageName.objects.create(name='dummy-package')

    def log_in_user(self):
        self.client.login(username=self.user.main_email, password=self.password)

    def post_to_view(self, package=None, email=None, ajax=True):
        post_params = {}
        if package:
            post_params['package'] = package
        if email:
            post_params['email'] = email
        kwargs = {}
        if ajax:
            kwargs = {
                'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest',
            }
        return self.client.post(
            reverse('pts-api-accounts-subscribe'), post_params, **kwargs)

    def test_subscribe_user(self):
        self.log_in_user()

        response = self.post_to_view(self.package.name, self.user.main_email)

        # After the POST, the user is subscribed to the package?
        self.assertTrue(self.user.is_subscribed_to(self.package))
        self.assertEqual('application/json', response['Content-Type'])
        expected = {
            'status': 'ok'
        }
        self.assertDictEqual(expected, json.loads(response.content))

    def test_subscribe_not_logged_in(self):
        """
        Tests that subscribing does not work when a user is not logged in.
        """
        self.post_to_view(self.package.name, self.user.main_email)

        # The user is not subscribed to the package
        self.assertFalse(self.user.is_subscribed_to(self.package))

    def test_subscribe_logged_in_not_owner(self):
        """
        Tests that a logged in user cannot subscribe an email that it does not
        own to a package.
        """
        self.log_in_user()
        other_user = User.objects.create_user(
            main_email='other@domain.com', password='asdf')

        response = self.post_to_view(self.package.name, other_user.main_email)

        # The user is not subscribed to the package
        self.assertFalse(other_user.is_subscribed_to(self.package))
        # Forbidden status code?
        self.assertEqual(403, response.status_code)

    def test_subscribe_multiple_emails(self):
        """
        Tests that a user can subscribe multiple emails at once.
        """
        self.user.emails.create(email='other@domain.com')
        self.log_in_user()

        self.post_to_view(
            email=[e.email for e in self.user.emails.all()], package=self.package.name)

        for email in self.user.emails.all():
            self.assertTrue(email.is_subscribed_to(self.package))

    def test_subscribe_multiple_emails_does_not_own_one(self):
        """
        Tests that no subscriptions are created if there is at least one email
        that the user does not own in the list of emails.
        """
        other_email = 'other@domain.com'
        EmailUser.objects.create(email=other_email)
        emails = [
            other_email,
            self.user.main_email,
        ]
        self.log_in_user()

        response = self.post_to_view(email=emails, package=self.package.name)

        self.assertEqual(403, response.status_code)


class UnsubscribeUserViewTests(TestCase):
    """
    Tests for the :class:`pts.accounts.views.UnsubscribeUserView` view.
    """
    def setUp(self):
        self.package = PackageName.objects.create(name='dummy-package')
        self.password = 'asdf'
        self.user = User.objects.create_user(
            main_email='user@domain.com', password=self.password)
        self.user.emails.create(email='other@domain.com')

    def subscribe_email_to_package(self, email, package_name):
        """
        Creates a subscription for the given email and package.
        """
        Subscription.objects.create_for(
            email=email,
            package_name=package_name)

    def log_in(self):
        self.client.login(username=self.user.main_email, password=self.password)

    def post_to_view(self, package, email=None, ajax=True):
        post_params = {
            'package': package,
        }
        if email:
            post_params['email'] = email
        kwargs = {}
        if ajax:
            kwargs = {
                'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest',
            }
        return self.client.post(
            reverse('pts-api-accounts-unsubscribe'), post_params, **kwargs)

    def test_unsubscribe_all_emails(self):
        """
        Tests the scenario where all the user's emails need to be unsubscribed
        from the given package.
        """
        for email in self.user.emails.all():
            self.subscribe_email_to_package(email.email, self.package.name)
        # Sanity check: the user is subscribed to the package
        self.assertTrue(self.user.is_subscribed_to(self.package))
        # Make sure the user is logged in
        self.log_in()

        response = self.post_to_view(package=self.package.name)

        # The user is no longer subscribed to the package
        self.assertFalse(self.user.is_subscribed_to(self.package))
        self.assertEqual('application/json', response['Content-Type'])

    def test_unsubscribe_not_logged_in(self):
        """
        Tests that the user cannot do anything when not logged in.
        """
        self.subscribe_email_to_package(self.user.main_email, self.package.name)

        self.post_to_view(self.package.name)

        # The user is still subscribed to the package
        self.assertTrue(self.user.is_subscribed_to(self.package))

    def test_unsubscribe_one_email(self):
        """
        Tests the scenario where only one of the user's email should be
        unsubscribed from the given package.
        """
        for email in self.user.emails.all():
            self.subscribe_email_to_package(email.email, self.package.name)
        # Sanity check: the user is subscribed to the package
        self.assertTrue(self.user.is_subscribed_to(self.package))
        # Make sure the user is logged in
        self.log_in()

        self.post_to_view(
            package=self.package.name, email=self.user.main_email)

        # The user is still considered subscribed to the package
        self.assertTrue(self.user.is_subscribed_to(self.package))
        # However, the main email is no longer subscribed
        for email in self.user.emails.all():
            if email.email == self.user.main_email:
                self.assertFalse(email.is_subscribed_to(self.package))
            else:
                self.assertTrue(email.is_subscribed_to(self.package))

    def test_package_name_not_provided(self):
        """
        Tests the scenario where the package name is not POSTed.
        """
        self.log_in()

        response = self.client.post(reverse('pts-api-accounts-unsubscribe'))

        self.assertEqual(404, response.status_code)
