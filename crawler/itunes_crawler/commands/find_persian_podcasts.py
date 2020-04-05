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
    try:
        for rss_entity in PodcastRss.select().where(PodcastRss.id >= start).order_by(PodcastRss.id.asc()):
            counter += 1
            if counter < 50:
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
                        'type': rss_xml.find(name='itunes:type').string,
                        'email': rss_xml.find(name='itunes:email').string,
                        'title': rss_xml.find(name='title').string,
                        'author': rss_xml.find(name='author').string,
                        'link': rss_xml.find(name='link').string,
                        'description': rss_xml.find(name='description').string,
                        'generator': rss_xml.find(name='generator').string,
                        'category': json.dumps([c['text'] for c in rss_xml.find_all(name='itunes:category')])
                    }

                    PersianPodcasts(**data).save(force_insert=True)
            except Exception as e:
                print(e, file=sys.stderr)
    finally:
        print('Last id:', last_id)


if __name__ == '__main__':
    find_persian_podcasts()
