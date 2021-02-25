#! /usr/bin/env bash
set -e

python app/celeryworker_pre_start.py

if [ $DAP_PORT ] ; then
    echo " * DAP is running!"
    python -m debugpy --listen 0.0.0.0:$DAP_PORT -m celery -A app.worker worker -l info -c 1
else
    celery -A app.worker worker -l info -c 1
fi
