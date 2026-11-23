web: gunicorn benefits.wsgi --log-file - --timeout 120
worker: env REMAP_SIGTERM=SIGQUIT celery --app benefits worker --queues benji_sms --concurrency 2 --loglevel INFO --without-gossip --without-mingle --without-heartbeat
