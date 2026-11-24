#!/usr/bin/env bash
# Heroku release phase (Procfile `release:`). Runs on the new slug in a one-off dyno before any
# dyno boots on it, so new code never takes traffic ahead of its schema or config. Any failure
# fails the release: Heroku doesn't deploy it, and the current release keeps serving.
#
# The current release keeps serving while this runs, so every migration has to work with the
# code already live (docs/DEPLOYMENT.md, "Migrations run before the new code").
#
# Heroku also runs this on config var changes and rollbacks; every command here is idempotent.
set -euo pipefail

echo "release: migrate"
python manage.py migrate --noinput

echo "release: sync_fpl_values"
python manage.py sync_fpl_values

echo "release: sync_feature_flags"
python manage.py sync_feature_flags

echo "release: add_config --all"
python manage.py add_config --all
