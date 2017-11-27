# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-07-10 05:56

from django.db import migrations


def drop_release_goals(apps, schema_editor):
    # We get the model from the versioned app registry;
    # if we directly import it, it'll be the wrong version
    ActionItemType = apps.get_model('core', 'ActionItemType')
    db_alias = schema_editor.connection.alias
    ActionItemType.objects.using(db_alias).filter(
		type_name='debian-release-goals-bugs').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_keywords_descriptions'),
    ]

    operations = [
        migrations.RunPython(
            drop_release_goals,
        ),
    ]
