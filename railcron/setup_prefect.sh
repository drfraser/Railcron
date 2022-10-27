#!/bin/bash -x

CURRDIR=`pwd`

## could set environment variables
# export PREFECT_ORION_DATABASE_CONNECTION_URL="sqlite+aiosqlite:////$currdir/.prefect/orion.db"
# export PREFECT_ORION_DATABASE_CONNECTION_URL="sqlite+aiosqlite:////tmp/orion.db"
# export PREFECT_LOGGING_LEVEL=INFO
# export PREFECT_LOGGING_SERVER_LEVEL=INFO
# export PREFECT_LOGGING_SETTINGS_PATH="$currdir/logging.yml"
# export PREFECT_LOGGING_SETTINGS_PATH="/tmp/logging.yml"

# profile for testing - logging to console, temp orion.db
# prefect profile create dryrun
prefect profile use dryrun
prefect config set PREFECT_LOGGING_LEVEL=INFO
prefect config set PREFECT_LOGGING_SERVER_LEVEL=INFO
prefect config set PREFECT_LOGGING_SETTINGS_PATH="$CURRDIR/dryrun_logging.yml"
prefect config set PREFECT_ORION_DATABASE_CONNECTION_URL="sqlite+aiosqlite:///$CURRDIR/dryrun_orion.db"

prefect profile use default
prefect config set PREFECT_LOGGING_LEVEL=INFO
prefect config set PREFECT_LOGGING_SERVER_LEVEL=WARNING
prefect config set PREFECT_LOGGING_SETTINGS_PATH="$CURRDIR/logging.yml"
prefect config set PREFECT_ORION_DATABASE_CONNECTION_URL="sqlite+aiosqlite:///$CURRDIR/orion.db"
prefect config set PREFECT_ORION_API_HOST=0.0.0.0   # `hostname -I | awk '{print $1}'`

# To start an instance of Prefect

## uvicorn logging fixed to INFO+ - have to edit Prefect code to adjust
# prefect orion start > /dev/null &

## create work queue for handling daily tasks
# prefect work-queue create daily_queue
# prefect agent start --hide-welcome -q 'daily_queue' &
