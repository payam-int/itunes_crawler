import json
import logging
import re
from datetime import datetime

import redis
import requests
from redis import Redis

redis = Redis(host='redis')

LOGGER = logging.getLogger('model')


class Proxy:
    MY_IP = requests.get('https://ifconfig.me/ip').content.decode('utf8')

    def __init__(self, proxy_info: dict):
        self._proxy_info = proxy_info

    def __str__(self):
        return "{ip}:{port}".format(**self._proxy_info)

    @staticmethod
    def _get_redis_key(id):
        return "PROXY:{}".format(id)

    def get_proxy_string(self):
        return "{type[0]}://{ip}:{port}".format(**self._proxy_info)

    def is_working(self):
        try:
            ip_response = requests.get('https://ifconfig.me/ip', timeout=5, proxies={
                'http': self.get_proxy_string(),
                'https': self.get_proxy_string()
            })

            ip = ip_response.content.decode('utf8')

            if re.match('\d+\.\d+\.\d+\.\d+', ip) and ip != Proxy.MY_IP:
                LOGGER.debug("Proxy %s is working", self.get_proxy_string())
                return True
        except Exception as e:
            LOGGER.debug(e)
        return False

    @staticmethod
    def get_k_oldest(k):
        ids = redis.zrange(Proxy._get_sorted_set_key(), 0, k)
        return Proxy.get_by_ids(ids)

    @staticmethod
    def get_by_ids(ids):
        values = redis.mget(map(lambda id: Proxy._get_redis_key(id.decode('utf-8')), ids))
        return list(map(lambda x: Proxy(json.loads(x)), values))

    @staticmethod
    def _get_sorted_set_key():
        return "PROXY_LIST"

    @staticmethod
    def _get_set_key():
        return "S:PROXY_LIST"

    @staticmethod
    def save(proxies):
        for proxy in proxies:
            redis.set(Proxy._get_redis_key(str(proxy)), json.dumps(proxy._proxy_info))
            redis.sadd(Proxy._get_set_key(), str(proxy))
            redis.zadd(Proxy._get_sorted_set_key(), {str(proxy): int(datetime.now().timestamp())})

    @staticmethod
    def delete(proxy_ids):
        for id in proxy_ids:
            redis.delete(Proxy._get_redis_key(id))
            redis.srem(Proxy._get_set_key(), id)
            redis.zrem(Proxy._get_sorted_set_key(), id)

    @staticmethod
    def get_total_count():
        return redis.zcount(Proxy._get_sorted_set_key(), '-inf', '+inf')
