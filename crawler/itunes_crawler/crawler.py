import gc
import logging
import re
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from prometheus_client import Summary
from requests import HTTPError

from itunes_crawler import settings
from itunes_crawler.models import Proxy

logger = logging.getLogger('itunes_crawler')
REQUEST_METRICS = Summary('http_request_profiling', 'Time spent getting a url', ('host',))
REQUEST_FAILURE_METRICS = Summary('http_request_exceptions_profiling', 'Time spent getting a url', ('host', 'type'))


def _get_proxy():
    # return {
    #     'http': 'socks5://proxy_broker:8888',
    #     'https': 'socks5://proxy_broker:8888',
    # }

    proxy = Proxy.get_random_proxy()
    if proxy:
        return {
            'http': proxy.get_proxy_string(),
            'https': proxy.get_proxy_string()
        }
    return None


def __get(url, proxy, *args, **kwargs):
    hostname = urlparse(url).hostname
    _kwargs = {'timeout': 10, 'proxies': proxy}
    _kwargs.update(kwargs)

    start_timer = time.perf_counter()
    try:
        response = requests.get(url, *args, **_kwargs)
        response.raise_for_status()
        REQUEST_METRICS.labels(hostname).observe(time.perf_counter() - start_timer)
        return response
    except HTTPError as e:
        error_label = 'HTTP{}'.format(e.response.status_code)
        REQUEST_FAILURE_METRICS.labels(hostname, error_label).observe(time.perf_counter() - start_timer)
        raise e
    except Exception as e:
        error_label = e.__class__.__name__
        REQUEST_FAILURE_METRICS.labels(hostname, error_label).observe(time.perf_counter() - start_timer)
        raise e


def _get(url, *args, **kwargs):
    try:
        proxy = _get_proxy()
        if proxy:
            return __get(url, proxy, *args, **kwargs)
    except Exception as e:
        pass
    return __get(url, settings.REQUESTS_PROXY, *args, **kwargs)


def _extract_itunes_id(link):
    return re.search('.+id(\d+)$', link).group(1)


def scrap_categories():
    url = 'https://podcasts.apple.com/us/genre/podcasts/id26'
    try:
        response = _get(url, timeout=10)
    except Exception as e:
        logger.error('scrap_categories.request',
                     extra={'url': url, 'exception': e})
        raise e
    try:
        categories_html = BeautifulSoup(response.content, "html.parser")
        top_level_categories = []
        for category in categories_html.select('.top-level-genre'):
            top_level_categories.append({
                'title': str(category.string),
                'link': str(category['href']),
                'id': _extract_itunes_id(str(category['href']))
            })
        return top_level_categories
    finally:
        categories_html.decompose()
        gc.collect()


CATEGORY_LETTERS = [chr(i) for i in range(ord('A'), ord('Z') + 1)] + ['*']


def scrap_category_page(url, letter, page):
    url = "{}?letter={}&page={}".format(url, letter, page)
    try:
        response = _get(url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        logger.error('scrap_category_page.request',
                     extra={'url': url, 'exception': e})
        raise e
    try:
        podcasts_html = BeautifulSoup(response.content.decode('utf-8'), "html.parser")

        for paginate_link in podcasts_html.select('ul.paginate li a'):
            if paginate_link.string and str(paginate_link.string) == str(page):
                break
        else:
            return []

        podcasts = []
        for podcast in podcasts_html.select('#selectedcontent ul>li a'):
            podcasts.append({
                'itunes_title': str(podcast.string),
                'itunes_link': str(podcast['href']),
                'id': _extract_itunes_id(str(podcast['href']))
            })
        return podcasts
    finally:
        podcasts_html.decompose()
        gc.collect()


def get_lookup(id):
    url = "https://itunes.apple.com/us/lookup?id=" + str(id)
    try:
        response = _get(url, timeout=30)
        response.raise_for_status()
        lookup = response.json()
        return lookup['results'][0] if 'feedUrl' in lookup['results'][0] else None
    except Exception as e:
        logger.error('Itunes Lookup failed.',
                     extra={'url': url, 'e': e})
        raise e
    finally:
        gc.collect()


def get_rss(url):
    rss = None
    try:
        response = _get(url, timeout=30)
        response.raise_for_status()
        return response.content.decode('utf-8')
    except Exception as e:
        logger.error('RSS Lookup failed.',
                     extra={'url': url, 'e': e})
        raise e
    finally:
        if rss: rss.decompose()
        gc.collect()
