# Copyright 2013-2015 The Distro Tracker Developers
# See the COPYRIGHT file at the top-level directory of this distribution and
# at https://deb.li/DTAuthors
#
# This file is part of Distro Tracker. It is subject to the license terms
# in the LICENSE file found in the top-level directory of this
# distribution and at https://deb.li/DTLicense. No part of Distro Tracker,
# including this file, may be copied, modified, propagated, or distributed
# except according to the terms contained in the LICENSE file.
"""
A skeleton of all vendor-specific function that can be implemented.
"""


def classify_message(msg, package=None, keyword=None):
    """
    The function should analyze the message and decides which package
    is affected and the keyword to use when relaying the message to
    subscribers.

    :param msg: The message to analyze
    :type msg: :py:class:`email.message.Message`

    :param str package: A suggested package. May be ``None``.
    :param str keyword: A suggested keyword. May be ``None``.
    """
    return (package, keyword)


def add_new_headers(received_message, package_name, keyword, team):
    """
    The function should return a list of two-tuples (header_name, header_value)
    which are extra headers that should be added to package messages before
    they are forwarded to subscribers.

    If no extra headers are wanted return an empty list or ``None``

    :param received_message: The original received package message
    :type received_message: :py:class:`email.message.Message`

    :param package_name: The name of the package for which the message was
        intended
    :type package_name: str

    :param keyword: The keyword with which the message is tagged.
    :type keyword: str

    :param team: The team slug for a message sent to the team or received
        through the team.
    :type team: str
    """
    pass


def approve_default_message(msg):
    """
    The function should return a ``Boolean`` indicating whether this message
    should be forwarded to subscribers which are subscribed to default
    keyword messages.

    :param msg: The original received package message
    :type msg: :py:class:`email.message.Message`
    """
    pass


def get_pseudo_package_list():
    """
    The function should return a list of pseudo-packages (their names) which
    are to be considered valid pseudo-packages.
    Any existing pseudo-packages which are no longer found in this list will be
    "demoted" to subscription-only packages, instead of being deleted.

    If there should be no update to the list, the function should return
    ``None``.
    """
    pass


def get_package_information_site_url(package_name,
                                     source_package=False,
                                     repository_name=None):
    """
    The function should return a URL to a package information Web page for
    the given package and repository. The repository parameter is optional.

    If no URL exists for the given parameters, returns ``None``.

    :param package_name: The name of the package for which the URL of the
        package information Web page should be given.
    :type package_name: string

    :param source_package: If ``True`` the function should consider the given
        package a source package, otherwise it should be considered a binary
        package.
    :type source_package: ``Boolean``

    :param repository_name: The name of the repository for which the package
        information should be provided.
    """
    pass


def get_developer_information_url(developer_email):
    """
    The function should return a URL to extra information about a
    developer, by email address.

    The function should return ``None`` if the vendor does not provide
    additional developer information or if it does not have the information for
    the particular developer email.

    In this case, on the package page, a <mailto> link will be provided,
    instead of the additional information.

    .. note::
       This function can be used by other modules apart from the general panel

    :param developer_email: The email of the developer for which a URL to a
        site with additional information should be given.
    :type developer_email: string
    """
    pass


def get_external_version_information_urls(package_name):
    """
    The function should return a list of external Web resources which provide
    additional information about the versions of a package.
    Each element of the list should be a dictionary with the keys:
    - url
    - description

    The function should return ``None`` if the vendor does not want to provide
    extra version information URLs.

    :param package_name: The name of the package for which external version
        information URLs should be provided.
    :type package_name: string
    """
    pass


def get_maintainer_extra(developer_email, package_name=None):
    """
    The function should return a list of additional items that are to be
    included in the general panel next to the maintainer.

    Each item needs to be a dictionary itself and can contain the following
    keys:
    - display
    - description
    - url

    .. note::
       Only the ``display`` key is mandatory.

    The function should return ``None`` if the vendor does not wish to include
    any extra items.

    :param developer_email: The email of the maintainer for which extra
        information is requested.
    :param package_name: The name of the package where the contributor is the
        maintainer and for which extra information should be provided.
        This parameter is included in case vendors want to provide different
        information based on the package page where the information will be
        displayed.
    """
    pass


def get_uploader_extra(developer_email, package_name=None):
    """
    The function should return a list of additional items that are to be
    included in the general panel next to an uploader.

    Each item needs to be a dictionary itself and can contain the following
    keys:
    - display
    - description
    - url

    .. note::
       Only the ``display`` key is mandatory.

    The function should return ``None`` if the vendor does not wish to include
    any extra items.

    :param developer_email: The email of the uploader for which extra
        information is requested.
    :param package_name: The name of the package where the contributor is an
        uploader and for which extra information should be provided.
        This parameter is included in case vendors want to provide different
        information based on the package page where the information will be
        displayed.
    """
    pass


def allow_package(stanza):
    """
    The function provides a way for vendors to exclude some packages from being
    saved in the database.

    :param stanza: The raw package entry from a ``Sources`` file.
    :type stanza: case-insensitive dict
    """
    pass


def get_extra_versions(package):
    """
    The function provides additional versions which should be displayed in the
    versions panel.

    Each version to be displayed should be a dict with the following keys:

    - version
    - repository_shorthand
    - version_link - optional
    - repository_link - optional

    The return value should be a list of such versions or ``None`` if the vendor
    does not wish to provide any additional versions.

    :param package: The package for which additional versions should be
        provided.
    :type package: :class:`PackageName <distro_tracker.core.models.PackageName>`
    """
    pass


def get_table_fields(table):
    """
    The function provides additional fields which should be displayed in a table

    One may add new specific :class:`BaseTableField`
    to the fields defined in the table's function :func:`default_fields
    <distro_tracker.core.package_tables.BasePackageTable.default_fields>`.
    However, it is also possible to redefine the entire list of
    :class:`BaseTableField` that must be displayed in the table.

    The return value should be a list of such table fields or ``None`` if the
    vendor does not wish to provide any additional fields.

    :param table: The table for which additional fields should be
        provided.
    :type table: :class:`BasePackageTable
        <distro_tracker.core.package_tables.BasePackageTable>`
    """
    pass


def additional_prefetch_related_lookups():
    """
    The function provides additional list of lookups to be prefetched along
    with the default lookups defined by :class:`BaseTableField
    <distro_tracker.core.package_tables.BaseTableField>`
    classes.

    The return value should be a list whose elements are either String or
    Prefetch objects
    """
    pass


def get_vcs_data(package):
    """
    The function provides additional data which should be displayed in the
    VCS table field.

    The return value should be a dictionary which will be merged with
    default context data defined by :func:`context
    <distro_tracker.core.package_tables.VcsTableField.context>` function.
    If this function is defined then its return value is simply passed to the
    template and does not require any special format; the vendor's template can
    access this value in the ``field.context`` context variable and can use it
    any way it wants.

    :param package: The package for which additional vcs data should be
        provided.
    :type package: :class:`PackageName
        <distro_tracker.core.models.PackageName>`
    """
    pass


def get_bug_display_manager_class():
    """
    The function must return the class responsible for handling the dysplaying
    logic of bugs data. To this end, vendors must define a new class
    that either inherits from :class:`BugDisplayManager
    <distro_tracker.core.models.BugDisplayManager>` or implements the same
    interface defined by it.
    """
    pass


def get_tables_for_team_page(team, limit):
    """
    The function must return a list of :class:`BasePackageTable` objects
    to be displayed in the main page of teams.

    :param team: The team for which the tables must be added.
    :type package: :class:`Team <distro_tracker.core.models.Team>`
    :param int limit: The number of packages to be displayed in the tables.
    """
    pass
