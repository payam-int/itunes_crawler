import gc
import logging
import re

from bs4 import BeautifulSoup

from itunes_crawler.proxy import get_by_proxy

logger = logging.getLogger('itunes_crawler')


def _get(url, *args, **kwargs):
    return get_by_proxy(url, *args, **kwargs)


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


PERSIAN_CHARS = ["آ ", "ا ", "ب ", "پ ", "ت ", "ث ", "ج ", "چ ", "ح ", "خ ", "د ", "ذ ", "ر ", "ز ", "ژ ", "س ", "ش ",
                 "ص ", "ض ", "ط ", "ظ ", "ع ", "غ ", "ف ", "ق ", "ک ", "گ ", "ل ", "م ", "ن ", "و ", "ه ", "ي ", "ء ",
                 "ة", "ئ"]
CATEGORY_LETTERS = [chr(i) for i in range(ord('A'), ord('Z') + 1)] + ['*'] + PERSIAN_CHARS


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
        podcasts = []
        for podcast in podcasts_html.select('#selectedcontent ul>li a'):
            podcasts.append({
                'title': str(podcast.string),
                'link': str(podcast['href']),
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
