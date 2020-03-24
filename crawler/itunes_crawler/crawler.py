import gc
import logging
import re
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from prometheus_client import Summary, Counter
from requests import ConnectTimeout, HTTPError

from itunes_crawler import settings

logger = logging.getLogger('itunes_crawler')
REQUEST_TIME = Summary('http_request_profiling', 'Time spent getting a url', ('host',))
EXCEPTION_COUNTER = Counter('http_exception_counter', 'Number of times with exception', ('host', 'type'))


def _get_proxy(hostname):
    if hostname in settings.SKIP_PROXY:
        return {}
    return settings.REQUESTS_PROXY


def _get(url, *args, **kwargs):
    hostname = urlparse(url).hostname
    _kwargs = {'timeout': 10, 'proxies': _get_proxy(hostname)}
    _kwargs.update(kwargs)

    try:
        start_timer = time.perf_counter()
        response = requests.get(url, *args, **_kwargs)
        response.raise_for_status()
        REQUEST_TIME.labels(hostname).observe(time.perf_counter() - start_timer)
        return response
    except ConnectTimeout as e:
        EXCEPTION_COUNTER.labels(hostname, 'ConnectTimeout').inc()
        raise e
    except HTTPError as e:
        error_label = 'HTTP{}'.format(e.response.status_code)
        EXCEPTION_COUNTER.labels(hostname, error_label).inc()
        raise e
    except Exception as e:
        EXCEPTION_COUNTER.labels(hostname, 'Exception').inc()
        raise e


def _extract_itunes_id(link):
    return re.search('.+id(\d+)$', link).group(1)


def scrap_categories():
    url = 'https://podcasts.apple.com/us/genre/podcasts/id26'
    try:
        response = _get(url, timeout=10, proxies=_get_proxy(url))
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
        response = _get(url, timeout=10, proxies=_get_proxy(url))
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
        response = _get(url, timeout=30, proxies=_get_proxy(url))
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
        response = _get(url, timeout=30, proxies=_get_proxy(url))
        response.raise_for_status()
        return response.content.decode('utf-8')
    except Exception as e:
        logger.error('RSS Lookup failed.',
                     extra={'url': url, 'e': e})
        raise e
    finally:
        if rss: rss.decompose()
        gc.collect()
