import logging
import time
from concurrent.futures.thread import ThreadPoolExecutor

from prometheus_client import Gauge

from proxy_pool.crawler import scrap
from proxy_pool.model import Proxy

LOGGER = logging.getLogger('app')
CURRENT_PROXIES = Gauge('current_proxies', 'Count of current proxies')


def bootstrap():
    jobs = [
        {'method': find_proxies, 'interval': 2 * 60, 'last_time': 0},
        {'method': evaluate_proxies, 'interval': 2 * 60, 'last_time': 0},
    ]

    while True:
        for job in jobs:
            if time.time() - job['last_time'] > job['interval']:
                try:
                    job['method']()
                    job['last_time'] = time.time()
                except Exception as e:
                    LOGGER.error(e)
        time.sleep(0.5)


def find_proxies():
    LOGGER.debug("Starting find proxy")
    start_link = 'https://hidemy.name/en/proxy-list/?anon=4'
    proxies = list(map(lambda p: Proxy(p), scrap(start_link)))

    with ThreadPoolExecutor(max_workers=10) as executor:
        for proxy in proxies:
            executor.submit(evaluate_proxy, proxy)


def evaluate_proxies():
    proxies = Proxy.get_k_oldest(100)
    LOGGER.debug("Starting evaluate job")
    with ThreadPoolExecutor(max_workers=10) as executor:
        for proxy in proxies:
            executor.submit(evaluate_proxy, proxy)
    CURRENT_PROXIES.set(Proxy.get_total_count())


def evaluate_proxy(proxy):
    if proxy.is_working():
        Proxy.save([proxy])
    else:
        Proxy.delete([str(proxy)])
