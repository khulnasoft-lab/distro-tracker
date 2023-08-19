# -*- coding: utf-8 -*-

from django.db import models, migrations


def forwards_func(apps, schema_editor):
    # We get the model from the versioned app registry;
    # if we directly import it, it'll be the wrong version
    Keyword = apps.get_model('core', 'Keyword')
    Architecture = apps.get_model('core', 'Architecture')
    MailingList = apps.get_model('core', 'MailingList')
    db_alias = schema_editor.connection.alias
    Keyword.objects.using(db_alias).bulk_create([
        Keyword(name='default', default=True,
                description='Anything else that cannot be better classified'),
        Keyword(name='bts', default=True,
                description='All bug reports and associated discussions'),
        Keyword(name='bts-control', default=True,
                description='Status changes of bug reports'),
        Keyword(name='summary', default=True,
                description='News about the status of the package'),
        Keyword(name='upload-source', default=True,
                description='Notifications of sourceful uploads'),
        Keyword(name='archive', default=True,
                description='Other notifications sent by the archive management tool'),
        Keyword(name='contact', default=True,
                description='Mails from people contacting the maintainer(s)'),
        Keyword(name='build', default=True,
                description='Notifications of build failures from build daemons'),
        Keyword(name='vcs', default=False,
                description='Commit notices of the VCS repository associated to the package'),
        Keyword(name='translation', default=False,
                description='Notifications about translations related to the package'),
        Keyword(name='upload-binary', default=False,
                description='Notifications of binary-only uploads (made by build daemons)'),
        Keyword(name='derivatives', default=False,
                description='Changes made to this package by derivatives'),
        Keyword(name='derivatives-bugs', default=False,
                description='Bug traffic about this package in derivative distributions'),
    ])
    Architecture.objects.using(db_alias).bulk_create([
        Architecture(name='all'),
        Architecture(name='alpha'),
        Architecture(name='amd64'),
        Architecture(name='any'),
        Architecture(name='arm'),
        Architecture(name='arm64'),
        Architecture(name='armeb'),
        Architecture(name='armel'),
        Architecture(name='armhf'),
        Architecture(name='avr32'),
        Architecture(name='hppa'),
        Architecture(name='hurd-i386'),
        Architecture(name='i386'),
        Architecture(name='ia64'),
        Architecture(name='kfreebsd-amd64'),
        Architecture(name='kfreebsd-i386'),
        Architecture(name='m32r'),
        Architecture(name='m68k'),
        Architecture(name='mips'),
        Architecture(name='mips64'),
        Architecture(name='mips64el'),
        Architecture(name='mipsel'),
        Architecture(name='mipsn32'),
        Architecture(name='mipsn32el'),
        Architecture(name='or1k'),
        Architecture(name='powerpc'),
        Architecture(name='powerpcel'),
        Architecture(name='powerpcspe'),
        Architecture(name='ppc64'),
        Architecture(name='ppc64el'),
        Architecture(name='s390'),
        Architecture(name='s390x'),
        Architecture(name='sh3'),
        Architecture(name='sh3eb'),
        Architecture(name='sh4'),
        Architecture(name='sh4eb'),
        Architecture(name='sparc'),
        Architecture(name='sparc64'),
        Architecture(name='x32'),
    ])
    MailingList.objects.using(db_alias).bulk_create([
        MailingList(name='debian', domain='lists.debian.org',
                    archive_url_template='https://lists.debian.org/{user}/'),
        MailingList(name='ubuntu', domain='lists.ubuntu.com',
                    archive_url_template='https://lists.ubuntu.com/archives/{user}/'),
        MailingList(name='riseup', domain='lists.riseup.net',
                    archive_url_template='https://lists.riseup.net/www/arc/{user}'),
        MailingList(name='launchpad', domain='lists.launchpad.net',
                    archive_url_template='https://lists.launchpad.net/{user}/'),
        MailingList(name='freedesktop', domain='lists.freedesktop.org',
                    archive_url_template='https://lists.freedesktop.org/archives/{user}/'),
        MailingList(name='lxde', domain='lists.lxde.org',
                    archive_url_template='http://lists.lxde.org/pipermail/{user}/'),
        MailingList(name='alioth-debian-net', domain='alioth-lists.debian.net',
                    archive_url_template='https://alioth-lists.debian.net/pipermail/{user}/'),
    ])


class Migration(migrations.Migration):

    initial = True

    replaces = [
        ('core', '0002_initial_data'),
        ('core', '0003_lxde_list_archives'),
        ('core', '0006_more_architectures'),
        ('core', '0007_keywords_descriptions'),
        ('core', '0016_aliothdebiannet_list_archives'),
    ]

    dependencies = [
        ('core', '0001_initial_v2'),
    ]

    operations = [
        migrations.RunPython(
            forwards_func,
        ),
    ]
