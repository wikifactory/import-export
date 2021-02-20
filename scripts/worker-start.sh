#! /usr/bin/env bash
set -e

python /app/celeryworker_pre_start.py

celery worker -A app.worker -l info -c 1
