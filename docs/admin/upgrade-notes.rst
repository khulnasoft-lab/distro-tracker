.. _upgrade-notes:

Upgrade Notes
=============

Update to Debian 12 / distro-tracker 1.2.x
------------------------------------------

Switching to Debian 12 implies updating Django to version 3.2 at least.

With distro-tracker version 1.2.0 we are still using the old
python3-django-jsonfield which is no longer available in Debian 12.
The field is again broken by a change in Django 3.2 but can be
worked around with a few settings (to be added in
/etc/distro-tracker/settings/local.py for example)::

    # Trick JSONField to work with pyscopg returning text instead of decoded objects
    import json
    JSONFIELD_ENCODER_CLASS = json.JSONEncoder
    JSONFIELD_DECODER_KWARGS = {
      'cls': json.JSONDecoder,
    }

With distro-tracker 1.2.1, the work-around is no longer needed because
the codebase has been switched to use the new JSONField provided
by Django itself.

Update to Debian 11 / distro-tracker 1.1.3
------------------------------------------

With the switch to Debian 11, and thus the switch to PostgreSQL 13
and python3-django-jsonfield 1.4.0, we are in a situation where
the JSONField assumes that the database fields are of type ``jsonb``.

This was usually not the case with the combination used in Debian 10, you
thus have to convert all your fields with the following SQL statements::

    ALTER TABLE debian_packageexcuses ALTER COLUMN excuses SET DATA TYPE jsonb USING excuses::jsonb;
    ALTER TABLE debian_lintianstats ALTER COLUMN stats SET DATA TYPE jsonb USING stats::jsonb;
    ALTER TABLE debian_buildlogcheckstats ALTER COLUMN stats SET DATA TYPE jsonb USING stats::jsonb;
    ALTER TABLE debian_ubuntupackage ALTER COLUMN bugs SET DATA TYPE jsonb USING bugs::jsonb;
    ALTER TABLE debian_ubuntupackage ALTER COLUMN patch_diff SET DATA TYPE jsonb USING patch_diff::jsonb;
    ALTER TABLE core_sourcepackage ALTER COLUMN vcs SET DATA TYPE jsonb USING vcs::jsonb;
    ALTER TABLE core_packagedata ALTER COLUMN value SET DATA TYPE jsonb USING value::jsonb;
    ALTER TABLE core_packagebugstats ALTER COLUMN stats SET DATA TYPE jsonb USING stats::jsonb;
    ALTER TABLE core_binarypackagebugstats ALTER COLUMN stats SET DATA TYPE jsonb USING stats::jsonb;
    ALTER TABLE core_actionitem ALTER COLUMN extra_data SET DATA TYPE jsonb USING extra_data::jsonb;
    ALTER TABLE core_sourcepackagedeps ALTER COLUMN details SET DATA TYPE jsonb USING details::jsonb;
    ALTER TABLE core_taskdata ALTER COLUMN data SET DATA TYPE jsonb USING data::jsonb;
