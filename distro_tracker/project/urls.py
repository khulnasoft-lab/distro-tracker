# Copyright 2013 The Distro Tracker Developers
# See the COPYRIGHT file at the top-level directory of this distribution and
# at https://deb.li/DTAuthors
#
# This file is part of Distro Tracker. It is subject to the license terms
# in the LICENSE file found in the top-level directory of this
# distribution and at https://deb.li/DTLicense. No part of Distro Tracker,
# including this file, may be copied, modified, propagated, or distributed
# except according to the terms contained in the LICENSE file.
"""The URL routes for the Distro Tracker project."""


import importlib

from django.conf import settings
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path, re_path
from django.views.generic import TemplateView

from distro_tracker.accounts.views import (
    AccountMergeConfirmView,
    AccountMergeConfirmedView,
    AccountMergeFinalize,
    AccountProfile,
    ChangePersonalInfoView,
    ChooseSubscriptionEmailView,
    ConfirmAddAccountEmail,
    ForgotPasswordView,
    LoginView,
    LogoutView,
    ManageAccountEmailsView,
    ModifyKeywordsView,
    PasswordChangeView,
    RegisterUser,
    RegistrationConfirmation,
    ResetPasswordView,
    SubscribeUserToPackageView,
    SubscriptionsView,
    UnsubscribeAllView,
    UnsubscribeUserView,
    UserEmailsView
)
from distro_tracker.core.news_feed import PackageNewsFeed
from distro_tracker.core.views import (
    ActionItemJsonView,
    ActionItemView,
    AddPackageToTeamView,
    AddTeamMember,
    ConfirmMembershipView,
    CreateTeamView,
    DeleteTeamView,
    EditMembershipView,
    IndexView,
    JoinTeamView,
    KeywordsView,
    LeaveTeamView,
    ManageTeam,
    OpenSearchDescription,
    PackageAutocompleteView,
    PackageNews,
    PackageSearchView,
    RemovePackageFromTeamView,
    RemoveTeamMember,
    SetMembershipKeywords,
    SetMuteTeamView,
    TeamAutocompleteView,
    TeamDetailsView,
    TeamListView,
    TeamPackagesTableView,
    TeamSearchView,
    UpdateTeamView,
    legacy_package_url_redirect,
    legacy_rss_redirect,
    news_page,
    package_page,
    package_page_redirect
)

admin.autodiscover()

urlpatterns = [
    # Redirects for the old PTS package page URLs
    re_path(r'^(?P<package_hash>(lib)?.)/(?P<package_name>(\1)[^/]+)\.html$',
            legacy_package_url_redirect),

    # Permanent redirect for the old RSS URL
    re_path(r'^(?P<package_hash>(lib)?.)/(?P<package_name>(\1)[^/]+)'
            r'/news\.rss20\.xml$',
            legacy_rss_redirect),

    path('search', PackageSearchView.as_view(),
         name='dtracker-package-search'),
    path('search.xml', OpenSearchDescription.as_view(),
         name='dtracker-opensearch-description'),
    path('favicon.ico',
         lambda r: redirect(settings.STATIC_URL + 'favicon.ico'),
         name='dtracker-favicon'),

    path('api/package/search/autocomplete', PackageAutocompleteView.as_view(),
         name='dtracker-api-package-autocomplete'),
    path('api/action-items/<int:item_pk>', ActionItemJsonView.as_view(),
         name='dtracker-api-action-item'),
    path('api/keywords/', KeywordsView.as_view(),
         name='dtracker-api-keywords'),
    path('api/teams/search/autocomplete', TeamAutocompleteView.as_view(),
         name='dtracker-api-team-autocomplete'),

    re_path(r'^admin/', admin.site.urls),

    path('news/<int:news_id>', news_page, name='dtracker-news-page'),
    path('news/<int:news_id>/', news_page),
    path('news/<int:news_id>/<slug:slug>/', news_page,
         name='dtracker-news-page'),
    path('action-items/<int:item_pk>', ActionItemView.as_view(),
         name='dtracker-action-item'),

    path('', IndexView.as_view(), name='dtracker-index'),

    # Account related URLs
    path('accounts/register/', RegisterUser.as_view(),
         name='dtracker-accounts-register'),
    path('accounts/+reset-password/+success/',
         TemplateView.as_view(
             template_name='accounts/password-reset-success.html'
         ),
         name='dtracker-accounts-password-reset-success'),
    path('accounts/+reset-password/<path:confirmation_key>/',
         ResetPasswordView.as_view(),
         name='dtracker-accounts-reset-password'),
    path('accounts/+forgot-password/', ForgotPasswordView.as_view(),
         name='dtracker-accounts-forgot-password'),
    path('accounts/register/success/',
         TemplateView.as_view(template_name='accounts/success.html'),
         name='dtracker-accounts-register-success'),
    path('accounts/+manage-emails/', ManageAccountEmailsView.as_view(),
         name='dtracker-accounts-manage-emails'),
    path('accounts/+confirm-new-email/<path:confirmation_key>/',
         ConfirmAddAccountEmail.as_view(),
         name='dtracker-accounts-confirm-add-email'),
    path('accounts/+merge-accounts/confirm/',
         AccountMergeConfirmView.as_view(),
         name='dtracker-accounts-merge-confirmation'),
    path('accounts/+merge-accounts/confirmed/',
         AccountMergeConfirmedView.as_view(),
         name='dtracker-accounts-merge-confirmed'),
    path('accounts/+merge-accounts/finalize/<path:confirmation_key>/',
         AccountMergeFinalize.as_view(),
         name='dtracker-accounts-merge-finalize'),
    path('accounts/+merge-accounts/finalized/',
         TemplateView.as_view(
             template_name='accounts/accounts-merge-finalized.html'),
         name='dtracker-accounts-merge-finalized'),
    path('accounts/confirm/<confirmation_key>',
         RegistrationConfirmation.as_view(),
         name='dtracker-accounts-confirm-registration'),
    path('accounts/profile/', AccountProfile.as_view(),
         name='dtracker-accounts-profile'),
    path('accounts/subscriptions/', SubscriptionsView.as_view(),
         name='dtracker-accounts-subscriptions'),
    path('accounts/profile/subscriptions/choose-subscription-email/',
         ChooseSubscriptionEmailView.as_view(),
         name='dtracker-accounts-choose-email'),
    path('accounts/login/', LoginView.as_view(),
         name='dtracker-accounts-login'),
    path('accounts/logout/', LogoutView.as_view(),
         name='dtracker-accounts-logout'),
    path('accounts/profile/modify/', ChangePersonalInfoView.as_view(),
         name='dtracker-accounts-profile-modify'),
    path('accounts/profile/password-change/', PasswordChangeView.as_view(),
         name='dtracker-accounts-profile-password-change'),

    path('api/accounts/profile/emails/', UserEmailsView.as_view(),
         name='dtracker-api-accounts-emails'),
    path('api/accounts/profile/subscribe/',
         SubscribeUserToPackageView.as_view(),
         name='dtracker-api-accounts-subscribe'),
    path('api/accounts/profile/unsubscribe/', UnsubscribeUserView.as_view(),
         name='dtracker-api-accounts-unsubscribe'),
    path('api/accounts/profile/unsubscribe-all/',
         UnsubscribeAllView.as_view(),
         name='dtracker-api-accounts-unsubscribe-all'),
    path('api/accounts/profile/keywords/', ModifyKeywordsView.as_view(),
         name='dtracker-api-accounts-profile-keywords'),
    path('accounts/profile/keywords', ModifyKeywordsView.as_view(),
         name='dtracker-accounts-profile-keywords'),

    # Team-related URLs
    path('teams/+create/', CreateTeamView.as_view(),
         name='dtracker-teams-create'),
    path('teams/<slug:slug>/+delete/', DeleteTeamView.as_view(),
         name='dtracker-team-delete'),
    path('teams/+delete-success/',
         TemplateView.as_view(template_name='core/team-deleted.html'),
         name='dtracker-team-deleted'),
    path('teams/<slug:slug>/+update/', UpdateTeamView.as_view(),
         name='dtracker-team-update'),
    path('teams/<slug:slug>/+add-package/', AddPackageToTeamView.as_view(),
         name='dtracker-team-add-package'),
    path('teams/<slug:slug>/+remove-package/',
         RemovePackageFromTeamView.as_view(),
         name='dtracker-team-remove-package'),
    path('teams/<slug:slug>/+join/', JoinTeamView.as_view(),
         name='dtracker-team-join'),
    path('teams/<slug:slug>/+leave/', LeaveTeamView.as_view(),
         name='dtracker-team-leave'),
    path('teams/<slug:slug>/+add-member/', AddTeamMember.as_view(),
         name='dtracker-team-add-member'),
    path('teams/<slug:slug>/+remove-member/', RemoveTeamMember.as_view(),
         name='dtracker-team-remove-member'),
    path('teams/<slug:slug>/+manage/', ManageTeam.as_view(),
         name='dtracker-team-manage'),
    path('teams/', TeamListView.as_view(),
         name='dtracker-team-list'),
    path('teams/+confirm/<path:confirmation_key>/',
         ConfirmMembershipView.as_view(),
         name='dtracker-team-confirm-membership'),
    path('team/+search', TeamSearchView.as_view(),
         name='dtracker-team-search'),
    path('teams/<slug:slug>/+mute/', SetMuteTeamView.as_view(action='mute'),
         name='dtracker-team-mute'),
    path('teams/<slug:slug>/+unmute/',
         SetMuteTeamView.as_view(action='unmute'),
         name='dtracker-team-unmute'),
    path('teams/<slug:slug>/+set-keywords/',
         SetMembershipKeywords.as_view(),
         name='dtracker-team-set-keywords'),
    path('teams/<slug:slug>/+manage-membership/',
         EditMembershipView.as_view(),
         name='dtracker-team-manage-membership'),
    path('teams/<slug:slug>/+table/<slug:table_slug>/',
         TeamPackagesTableView.as_view(),
         name='dtracker-team-general-table'),
    path('teams/<slug:slug>/', TeamDetailsView.as_view(),
         name='dtracker-team-page'),

    # Package  news page
    path('pkg/<package_name>/news/', PackageNews.as_view(),
         name='dtracker-package-news'),

    # Dedicated package page
    re_path(r'^pkg/(?P<package_name>[^/]+)/?$', package_page,
            name='dtracker-package-page'),
    # RSS news feed
    path('pkg/<package_name>/rss', PackageNewsFeed(),
         name='dtracker-package-rss-news-feed'),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', django.contrib.admindocs.urls),
]

for app in settings.INSTALLED_APPS:
    try:
        urlmodule = importlib.import_module(app + '.tracker_urls')
        if hasattr(urlmodule, 'urlpatterns'):
            urlpatterns += urlmodule.urlpatterns
    except ImportError:
        pass

urlpatterns += [
    # The package page view catch all. It must be listed *after* the admin
    # URL so that the admin URL is not interpreted as a package named "admin".
    re_path(r'^(?P<package_name>[^/]+)/?$', package_page_redirect,
            name='dtracker-package-page-redirect'),
]

if settings.DJANGO_EMAIL_ACCOUNTS_USE_CAPTCHA:
    import captcha.urls
    urlpatterns += [
        re_path(r'^captcha/', include(captcha.urls.urlpatterns)),
    ]

if settings.DEBUG:
    import django.views.static
    import debug_toolbar
    urlpatterns = [
        re_path(r'^media/(?P<path>.*)$', django.views.static.serve,
                {'document_root': settings.MEDIA_ROOT}),
        re_path(r'^static/(?P<path>.*)$', django.views.static.serve,
                {'document_root': settings.STATIC_ROOT}),
        re_path(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
