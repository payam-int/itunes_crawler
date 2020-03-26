import threading

import prometheus_client

from itunes_crawler import settings
from itunes_crawler.app import bootstrap, worker

prometheus_client.start_http_server(int(settings.PROMETHEUS_PORT))

RUNNING_JOBS_METRIC = prometheus_client.Gauge('running_jobs', 'Number of running jobs')

bootstrap()
threads = [threading.Thread(target=worker) for _ in range(0, int(settings.WORKERS_COUNT))]
for thread in threads:
    thread.start()

running_jobs = len(threads)
RUNNING_JOBS_METRIC.set(running_jobs)

for thread in threads:
    thread.join()
    running_jobs -= 1
    RUNNING_JOBS_METRIC.set(running_jobs)
