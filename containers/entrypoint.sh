#!/bin/sh

set -x

# Start postgresql for the benefit of everything
/etc/init.d/postgresql start
su postgres - -c "createuser -d root"

# Setup the database for the Django application
if [ -e /app/manage.py ]; then
    cd /app
    ./manage.py migrate
fi

if [ -n "$1" ]; then
    exec "$@"
else
    exec /bin/bash
fi
