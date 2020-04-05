import logging
import time
from datetime import datetime, timedelta

import requests
from peewee import Function, Select
from prometheus_client import Summary

from itunes_crawler import crawler, settings
from itunes_crawler.models import Job, db, db_models, TopLevelCategory, Podcast, PodcastItunesLookup, PodcastRss

logger = logging.getLogger('app')
JOB_METRICS = Summary('job_processing_profiling', 'Time spent processing job', ('type', 'result'))


def bootstrap():
    lock_query = Select().select(Function('pg_try_advisory_lock', [settings.JOB_LOCK_PREFIX, 0])).execute(db)
    if lock_query[0]['pg_try_advisory_lock']:
        try:
            for db_model in db_models:
                db.create_tables([db_model])
        finally:
            Select().select(Function('pg_advisory_unlock', [settings.JOB_LOCK_PREFIX, 0])).execute(db)
    try:
        Job(type=Job.Types.TOP_LEVEL_CATEGORIES, interval=48 * 3600).save(force_insert=True)
    except Exception as e:
        logger.error(e)

    for i in range(0, 15):
        try:
            ip = requests.get('https://ifconfig.me/ip', timeout=10, proxies=settings.REQUESTS_PROXY)
            if len(ip.content) > 0:
                logger.info("Connected to the internet.")
                break
        except Exception as e:
            logger.warning(e, extra={'proxy': settings.REQUESTS_PROXY})
        time.sleep(10)
        logger.info("Waiting for the internet connection...")
    else:
        logger.error("Could not connect to the internet.")
        exit(1)


def worker():
    while True:
        try:
            start_timer = time.perf_counter()

            job = Job.take()
            if not job:
                time.sleep(5)
                continue
            try:

                if job.type == Job.Types.TOP_LEVEL_CATEGORIES:
                    crawl_top_categories(job)
                elif job.type == Job.Types.CATEGORY_LETTER:
                    crawl_category(job)
                elif job.type == Job.Types.PODCAST_LOOKUP:
                    crawl_podcast(job)

                job.next_time_at = datetime.now() + timedelta(seconds=job.interval)
                job.last_success_at = datetime.now()
                job.save()
                JOB_METRICS.labels(job.type, 'SUCCESS').observe(time.perf_counter() - start_timer)
            except Exception as e:
                job.next_time_at = job.next_time_at + timedelta(seconds=60)
                job.save()
                JOB_METRICS.labels(job.type, 'FAIL').observe(time.perf_counter() - start_timer)
                raise e
            finally:
                job.release()
        except Exception as e:
            logger.error(e, extra={'exception': e})


def crawl_top_categories(job):
    top_categories = crawler.scrap_categories()
    TopLevelCategory.insert_many(top_categories).on_conflict_ignore().execute()
    jobs = []
    for top_category in top_categories:
        for letter in crawler.CATEGORY_LETTERS:
            jobs.append({
                'type': Job.Types.CATEGORY_LETTER,
                'metadata': {'letter': letter, 'id': top_category['id']},
                'interval': 48 * 3600
            })
    Job.insert_many(jobs).on_conflict_ignore().execute()


def crawl_category(job):
    metadata = job.metadata
    category = TopLevelCategory.get_by_id(metadata['id'])
    try:
        page = 0
        while True:
            page += 1
            podcasts = crawler.scrap_category_page(category.link, metadata['letter'], page)
            if not len(podcasts):
                return

            for podcast in podcasts:
                podcast.update({'category_id': category.id, 'category_page': page,
                                'category_letter': metadata['letter']})

            Podcast.insert_many(podcasts).on_conflict_ignore().execute(db)

            jobs = []
            for podcast in podcasts:
                jobs.append({
                    'type': Job.Types.PODCAST_LOOKUP,
                    'interval': 48 * 3600,
                    'metadata': {'id': podcast['id']}
                })

            Job.insert_many(jobs).on_conflict_ignore().execute(db)
    except Exception as e:
        raise e


def crawl_podcast(job):
    metadata = job.metadata
    podcast = Podcast.get_by_id(metadata['id'])
    podcast_lookup = PodcastItunesLookup.get_or_none(id=podcast.id)
    try:
        lookup = crawler.get_lookup(metadata['id'])
        if lookup:
            podcast_lookup = podcast_lookup or PodcastItunesLookup(id=podcast.id)
            podcast_lookup.itunes_lookup = lookup
            podcast_lookup.updated_at = datetime.now()
            podcast_lookup.save() or podcast_lookup.save(force_insert=True)

    except Exception as e:
        raise e

    if podcast_lookup and 'feedUrl' in podcast_lookup.itunes_lookup:
        feed_url = podcast_lookup.itunes_lookup['feedUrl']
        rss = crawler.get_rss(feed_url)
        podcast_rss = PodcastRss.get_or_none(id=podcast.id) or PodcastRss(id=podcast.id)
        podcast_rss.rss = rss
        podcast_rss.updated_at = datetime.now()
        podcast_rss.save() or podcast_rss.save(force_insert=True)
