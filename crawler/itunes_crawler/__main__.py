import logging
import sys
import threading

import graypy
import prometheus_client

from itunes_crawler import settings
from itunes_crawler.app import worker

prometheus_client.start_http_server(int(settings.PROMETHEUS_PORT))

logging_handlers = []
if settings.GRAYLOG_GELFUDP_LOGGER is not None:
    graylog_handler = graypy.GELFUDPHandler(settings.GRAYLOG_GELFUDP_LOGGER['host'],
                                            int(settings.GRAYLOG_GELFUDP_LOGGER['port']))
    logging_handlers.append(graylog_handler)
if settings.CONSOLE_LOGGER:
    console_handler = logging.StreamHandler(sys.stdout)
    logging_handlers.append(console_handler)

logging.basicConfig(level=int(settings.LOGGING_LEVEL), handlers=logging_handlers, format=settings.LOGGING_FORMAT)

RUNNING_JOBS_METRIC = prometheus_client.Gauge('running_jobs', 'Number of running jobs')

threads = [threading.Thread(target=worker) for _ in range(0, int(settings.WORKERS_COUNT))]
for thread in threads:
    thread.start()

running_jobs = len(threads)
RUNNING_JOBS_METRIC.set(running_jobs)

for thread in threads:
    thread.join()
    running_jobs -= 1
    RUNNING_JOBS_METRIC.set(running_jobs)
