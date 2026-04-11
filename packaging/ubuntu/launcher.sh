#!/bin/sh
set -eu

APP_ROOT="/opt/production-logging-center-glc"
exec "$APP_ROOT/production-logging-center-glc" "$@"