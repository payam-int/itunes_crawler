import datetime
import logging
import time
from abc import ABC, abstractmethod

from prometheus_client import Summary

from itunes_crawler import crawler
from itunes_crawler.models2 import Session, ScheduledJob, ScheduledJobTypes, ItunesTopLevelCategory, ItunesListPodcast, \
    ItunesPodcastLookup, ItunesPodcastRss

logger = logging.getLogger('app')
JOB_METRICS = Summary('job_processing_profiling', 'Time spent processing job', ('type'))
TAKING_JOB_METRICS = Summary('taking_job_profiling', 'Time spent taking a job', ())
LOOP_METRICS = Summary('loop_profiling', 'Time spent on loop', ())


def worker():
    job_executor = JobExecutor.get()
    while True:
        with LOOP_METRICS.time():
            try:
                time.sleep(0.1)
                session = Session()
                job = None
                with TAKING_JOB_METRICS.time():
                    job = (ScheduledJob.take(session)[:] or [None])[0]

                try:
                    if job:
                        with JOB_METRICS.labels(job.type).time():
                            job_executor.execute(session, job)
                        job.success(datetime.timedelta(days=2))
                        session.add(job)
                    else:
                        time.sleep(1)
                except Exception as e:
                    session.rollback()
                    job.fail()
                    session.add(job)
                finally:
                    session.commit()
                    session.close()
            except Exception as e:
                logger.exception(e)


class JobExecutor(ABC):
    @staticmethod
    def get():
        exec = CrawlCategoriesJob()
        exec.set_next(CrawlCategoryPageJob()) \
            .set_next(GetPodcastLookup()) \
            .set_next(GetPodcastRss())

        return exec

    def __init__(self):
        self.next = None

    def set_next(self, next: 'JobExecutor'):
        self.next = next
        return next

    def execute(self, session, job: ScheduledJob):
        if self._is_responsible(job):
            return self._execute(session, job)
        else:
            if self.next:
                return self.next.execute(session, job)
            return False

    @abstractmethod
    def _is_responsible(self, job):
        pass

    @abstractmethod
    def _execute(self, session, job):
        pass


class CrawlCategoriesJob(JobExecutor):
    def _is_responsible(self, job):
        return job.type == ScheduledJobTypes.TOP_LEVEL_CATEGORIES

    def _execute(self, session, job):
        categories = crawler.scrap_categories()
        for category in categories:
            category_entity = ItunesTopLevelCategory(
                itunes_id=category['id'],
                title=category['title'],
                link=category['link'],
            )
            session.merge(category_entity)
            for letter in crawler.CATEGORY_LETTERS:
                new_job_identifier = "{0}::{1}".format(category['id'], letter)
                new_job = ScheduledJob(
                    type=ScheduledJobTypes.CATEGORY_LETTER,
                    id=new_job_identifier,
                    meta={'letter': letter, 'id': category['id']}
                )
                session.merge(new_job)


class CrawlCategoryPageJob(JobExecutor):
    def _is_responsible(self, job):
        return job.type == ScheduledJobTypes.CATEGORY_LETTER

    def _execute(self, session, job):
        metadata = job.meta
        category = session.query(ItunesTopLevelCategory) \
            .filter(ItunesTopLevelCategory.itunes_id == str(metadata['id'])) \
            .first()
        page = 0
        while True:
            page += 1
            podcasts = crawler.scrap_category_page(category.link, metadata['letter'].strip(), page)
            for podcast in podcasts:
                podcast_entity = ItunesListPodcast(
                    itunes_id=podcast['id'],
                    title=podcast['title'],
                    link=podcast['link'],
                    itunes_category_id=category.itunes_id,
                    category_letter=metadata['letter'].strip(),
                    category_page=page
                )

                session.merge(podcast_entity)

                new_job = ScheduledJob(
                    type=ScheduledJobTypes.PODCAST_LOOKUP,
                    id=podcast['id'],
                    meta={'itunes_id': podcast['id']},
                )

                session.merge(new_job)
            if not len(podcasts) or len(podcasts) == 1:
                return


class GetPodcastLookup(JobExecutor):
    def _is_responsible(self, job):
        return job.type == ScheduledJobTypes.PODCAST_LOOKUP

    def _execute(self, session, job):
        metadata = job.meta
        lookup = crawler.get_lookup(metadata['itunes_id'])
        if lookup:
            lookup_entity = ItunesPodcastLookup(
                itunes_id=metadata['itunes_id'],
                itunes_lookup=lookup
            )
            session.merge(lookup_entity)

            new_job = ScheduledJob(
                type=ScheduledJobTypes.PODCAST_RSS,
                id=metadata['itunes_id'],
                meta={'itunes_id': metadata['itunes_id']},
            )

            session.merge(new_job)


class GetPodcastRss(JobExecutor):
    def _is_responsible(self, job):
        return job.type == ScheduledJobTypes.PODCAST_RSS

    def _execute(self, session, job):
        metadata = job.meta
        itunes_podcast = session \
            .query(ItunesPodcastLookup) \
            .filter_by(itunes_id=str(metadata['itunes_id'])) \
            .first()
        if itunes_podcast and 'feedUrl' in itunes_podcast.itunes_lookup:
            itunes_lookup = itunes_podcast.itunes_lookup
            feed_url = itunes_lookup['feedUrl']

            rss = crawler.get_rss(feed_url)
            rss_entity = ItunesPodcastRss(
                itunes_id=metadata['itunes_id'],
                rss=rss
            )

            session.merge(rss_entity)
