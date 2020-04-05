import json
import sys

import click
from bs4 import BeautifulSoup

from itunes_crawler.models import PersianPodcasts, PodcastRss


@click.command()
@click.option('-s', '--start', type=int, default=0)
def find_persian_podcasts(start):
    last_id = 0
    counter = 0
    total_counts = PodcastRss.select().where(PodcastRss.id >= start).count()
    print(total_counts, 'total items.')
    page_size = 100
    pages = int(total_counts / page_size)
    try:
        for current_page in range(0, pages + 1):
            for rss_entity in PodcastRss.select().where(PodcastRss.id >= start).order_by(PodcastRss.id.asc()).paginate(
                    current_page, page_size):
                counter += 1
                if counter < 20:
                    print(counter, 'items checked')
                if counter % 1000 == 0:
                    print(counter, 'items checked.')
                last_id = rss_entity.id
                rss_text = str(rss_entity.rss).strip('\n\uFEFF ')
                try:
                    rss_xml = BeautifulSoup(rss_text, 'xml')
                    language_tag = rss_xml.select_one('rss channel language')
                    if language_tag and language_tag.string == 'fa':
                        data = {
                            'id': rss_entity.id,
                            'category': json.dumps([c['text'] for c in rss_xml.find_all(name='itunes:category')])
                        }
                        data_elements = {
                            'type': rss_xml.find(name='itunes:type'),
                            'email': rss_xml.find(name='itunes:email'),
                            'title': rss_xml.find(name='title'),
                            'author': rss_xml.find(name='author'),
                            'link': rss_xml.find(name='link'),
                            'description': rss_xml.find(name='description'),
                            'generator': rss_xml.find(name='generator'),
                        }

                        for elem in data_elements:
                            data[elem] = data_elements[elem].string if data_elements[elem] else ''

                        PersianPodcasts(**data).save(force_insert=True)
                except Exception as e:
                    print(e, file=sys.stderr)
                    print('id', last_id)
    finally:
        print('Last id:', last_id)


if __name__ == '__main__':
    find_persian_podcasts()
