import threading

import prometheus_client

from itunes_crawler import settings
from itunes_crawler.app import bootstrap, worker

prometheus_client.start_http_server(int(settings.PROMETHEUS_PORT))

bootstrap()
threads = [threading.Thread(target=worker) for _ in range(0, int(settings.WORKERS_COUNT))]
for thread in threads:
    thread.start()

for thread in threads:
    thread.join()
