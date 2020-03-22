import gc
import logging
import re

import requests
from bs4 import BeautifulSoup

from itunes_crawler import settings

logger = logging.getLogger('itunes_crawler')


def _extract_itunes_id(link):
    return re.search('.+id(\d+)$', link).group(1)


def scrap_categories():
    link = 'https://podcasts.apple.com/us/genre/podcasts/id26'
    try:
        response = requests.get(link, timeout=10, proxies=settings.REQUESTS_PROXY)
        response.raise_for_status()
    except Exception as e:
        logger.error('scrap_categories.request',
                     extra={'url': link, 'exception': e})
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
    link = "{}?letter={}&page={}".format(url, letter, page)
    try:
        response = requests.get(link, timeout=10, proxies=settings.REQUESTS_PROXY)
        response.raise_for_status()
    except Exception as e:
        logger.error('scrap_category_page.request',
                     extra={'url': link, 'exception': e})
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
        request = requests.get(url, timeout=30, proxies=settings.REQUESTS_PROXY)
        request.raise_for_status()
        lookup = request.json()
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
        response = requests.get(url, timeout=30, proxies=settings.REQUESTS_PROXY)
        response.raise_for_status()
        return response.content.decode('utf-8')
    except Exception as e:
        logger.error('RSS Lookup failed.',
                     extra={'url': url, 'e': e})
        raise e
    finally:
        if rss: rss.decompose()
        gc.collect()
