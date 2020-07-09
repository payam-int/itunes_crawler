import gc

from bs4 import BeautifulSoup

from itunes_crawler.crawler import PERSIAN_CHARS


class PodcastRSSParser:
    def extract(self, rss):
        rss = self._cleanup(rss)
        xml = BeautifulSoup(rss, 'xml')
        try:
            headers = self._extract_headers(xml)
            items = self._extract_items(xml)

            return {
                **headers,
                'items': items
            }
        finally:
            xml.decompose()
            gc.collect()

    def _cleanup(self, rss):
        return rss.strip('\n\uFEFF ')

    def _extract_children(self, elem, fields):
        if not elem:
            return dict()
        result = dict()
        for elem_name in fields:
            child = elem.find(name=elem_name, recursive=False)
            result[elem_name] = str(child.string) if child else None
        return result

    def _extract_headers(self, xml):
        headers = self._extract_children(xml.channel,
                                         ['title', 'description', 'link', 'generator', 'lastBuildDate', 'author',
                                          'copyright', 'language', 'itunes:author', 'itunes:summary',
                                          'itunes:type'])
        headers['itunes_category'] = [str(c['text']) for c in xml.find_all(name='itunes:category')]

        itunes_owner = xml.channel.find(name='itunes:owner', recursive=False)
        if itunes_owner:
            headers['itunes:owner'] = self._extract_children(itunes_owner, ['itunes:email', 'itunes:name'])

        return headers

    def _extract_items(self, xml):
        items = []
        for item in xml.channel.find_all(name='item', recursive=False):
            item_fields = self._extract_children(item, ['title', 'description', 'link', 'pubDate', 'itunes:duration',
                                                        'itunes:episode'])
            items.append(item_fields)
        return items


class PersianPodcastClassifier:
    def classify(self, rss_json):
        language = rss_json['language']
        if language:
            if 'fa' in language or 'ir' in language:
                return 2

            if 'ar' in language:
                return 0

        for persian_letter in PERSIAN_CHARS:
            for key in ['title', 'description', 'itunes:summary']:
                if rss_json[key] and persian_letter in rss_json[key]:
                    return 1
            for item in rss_json['items']:
                if item['title'] and persian_letter in item['title'] or \
                        item['description'] and persian_letter in item['description']:
                    return 1
        return 0
