import logging
import time
from contextlib import ContextDecorator
from datetime import datetime
from urllib.parse import urlparse

import requests
from prometheus_client import Summary, Counter
from requests import HTTPError

logger = logging.getLogger('itunes_crawler.proxy')
REQUEST_METRICS = Summary('http_request_profiling', 'Time spent getting a url', ('host', 'proxy'))
REQUEST_FAILURE_METRICS = Summary('http_request_exceptions_profiling', 'Time spent getting a url',
                                  ('host', 'type', 'proxy'))
NO_PROXY_METRICS = Counter('no_proxy_counter', 'counts when there is no proxy available', ('type',))


class CircuitBrokenException(Exception):
    pass


class Circuit:
    def __init__(self):
        self.blocked = False
        self.block_timestamp = None
        self.errors = 0
        self.last_expire = None

    def check(self):
        return not self.blocked or self.block_timestamp < datetime.now().timestamp() - 5 * 60

    def failed(self):
        if self.blocked and self.block_timestamp < datetime.now().timestamp() - 5 * 60:
            self.blocked = False
            self.errors = 0
        if self.last_expire is None:
            self.last_expire = datetime.now().timestamp()
        if self.last_expire < datetime.now().timestamp() - 3600:
            self.last_expire = datetime.now().timestamp()
            self.errors = self.errors / 2
        self.errors += 1
        if self.errors > 100:
            self.blocked = True
            self.block_timestamp = datetime.now().timestamp()


class ProxyFactory(ContextDecorator):
    PROXIES = {
        'tor': {
            'http': 'socks5://tor:9050',
            'https': 'socks5://tor:9050',
        },
        'no-proxy': None,
    }

    def __init__(self):
        self.circuits = dict()

    def _get_key(self, proxy_name, hostname):
        return "{}::{}".format(proxy_name, hostname)

    def get_proxy(self, hostname):
        for proxy_name in ProxyFactory.PROXIES:
            key = self._get_key(proxy_name, hostname)
            if key not in self.circuits or self.circuits[key].check():
                return proxy_name, ProxyFactory.PROXIES[proxy_name]
        NO_PROXY_METRICS.labels(hostname).inc()
        raise CircuitBrokenException('No proxy for {}'.format(hostname))

    def failed(self, hostname, proxy_name):
        key = self._get_key(proxy_name, hostname)
        if key not in self.circuits:
            self.circuits[key] = Circuit()
        self.circuits[key].failed()
        logger.warning("Circuit %s :: %s broken", proxy_name, hostname)


proxy_factory = ProxyFactory()


def get_by_proxy(url, *args, **kwargs):
    hostname = urlparse(url).hostname

    proxy_name, proxy = proxy_factory.get_proxy(hostname)

    _kwargs = {'timeout': 20, 'proxies': proxy}
    _kwargs.update(kwargs)

    start_timer = time.perf_counter()
    try:
        response = requests.get(url, *args, **_kwargs)
        response.raise_for_status()
        REQUEST_METRICS.labels(hostname, proxy_name).observe(time.perf_counter() - start_timer)
        return response
    except HTTPError as e:
        error_label = 'HTTP{}'.format(e.response.status_code)
        REQUEST_FAILURE_METRICS.labels(hostname, error_label, proxy_name).observe(time.perf_counter() - start_timer)

        if e.response.status_code in [403, 503]:
            proxy_factory.failed(hostname, proxy_name)

        raise e
    except Exception as e:
        error_label = e.__class__.__name__
        REQUEST_FAILURE_METRICS.labels(hostname, error_label, proxy_name).observe(time.perf_counter() - start_timer)
        raise e


print(get_by_proxy('https://ifconfig.me/ip'))
