import logging

import click
from dateutil.parser import parse as parse_date

from itunes_crawler.models2 import Session, ItunesPodcastRss, Podcast, PodcastFeedData
from itunes_crawler.podcast_rss import PodcastRSSParser, PersianPodcastClassifier

logger = logging.getLogger('find_persian_podcasts')


@click.command()
@click.option('-s', '--start', type=int, default=0)
def find_persian_podcasts(start):
    session = Session()
    last_id = str(start)
    podcast_rss_parser = PodcastRSSParser()
    persian_podcast_classifier = PersianPodcastClassifier()
    while True:
        podcasts_rss = session \
            .query(ItunesPodcastRss) \
            .filter(ItunesPodcastRss.itunes_id > last_id) \
            .order_by(ItunesPodcastRss.itunes_id) \
            .limit(50) \
            .all()

        if not podcasts_rss:
            break
        for podcast_rss in podcasts_rss:
            podcast_data = None
            try:
                podcast_data = podcast_rss_parser.extract(podcast_rss.rss)
                feed_data = PodcastFeedData(
                    itunes_id=podcast_rss.itunes_id,
                    feed=podcast_data
                )
                session.merge(feed_data)

                is_persian = persian_podcast_classifier.classify(podcast_data)
                last_episode_release = parse_date(podcast_data['items'][0]['pubDate']) if podcast_data[
                    'items'] else None
                episodes = len(podcast_data['items'])

                itunes_rss_data = Podcast(
                    itunes_id=podcast_rss.itunes_id,
                    title=podcast_data['title'],
                    description=podcast_data['description'],
                    link=podcast_data['link'],
                    generator=podcast_data['generator'],
                    last_build_date=parse_date(podcast_data['lastBuildDate']) if podcast_data[
                        'lastBuildDate'] else None,
                    author=podcast_data['author'],
                    email=podcast_data['itunes:owner']['itunes:email'] if 'itunes:owner' in podcast_data else None,
                    copyright=podcast_data['copyright'],
                    language=podcast_data['language'],
                    itunes_type=podcast_data['itunes:type'],
                    category=podcast_data['itunes_category'],
                    last_episode_release=last_episode_release,
                    episodes=episodes,
                    is_persian=is_persian
                )
                session.merge(itunes_rss_data)
            except Exception as e:
                logger.exception(e, itunes_id=podcast_rss.itunes_id)
            last_id = podcast_rss.itunes_id
        session.commit()
        print(last_id)


if __name__ == '__main__':
    find_persian_podcasts()
