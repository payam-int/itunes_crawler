import datetime
import json
import logging
import signal

import peewee_extra_fields
from peewee import PostgresqlDatabase, Model, CharField, TextField, DateTimeField, IntegerField, AutoField, \
    ForeignKeyField
from redis import Redis

from itunes_crawler import settings

logger = logging.getLogger('models')
db = PostgresqlDatabase(settings.POSTGRES['database'], host=settings.POSTGRES['host'],
                        port=settings.POSTGRES['port'], user=settings.POSTGRES['user'],
                        password=settings.POSTGRES['password'], autocommit=True, autorollback=True,
                        field_types=peewee_extra_fields.FIELD_TYPES, thread_safe=True)

logger.info("Connected to database...")

redis = Redis(host='redis')


def close_db():
    logger.info("Closing the database connection...")
    db.close()


signal.signal(signal.SIGTERM, close_db)
signal.signal(signal.SIGINT, close_db)


class JSONField(TextField):
    def db_value(self, value):
        return json.dumps(value)

    def python_value(self, value):
        return json.loads(value) if value is not None else None


class BaseModel(Model):
    class Meta:
        database = db


class Job(BaseModel):
    class Types:
        CATEGORY_LETTER = 'CATEGORY_LETTER'
        TOP_LEVEL_CATEGORIES = 'TOP_LEVEL_CATEGORIES'
        PODCAST_LOOKUP = 'PODCAST_LOOKUP'

    id = AutoField(primary_key=True)
    type = CharField(index=True)
    metadata = JSONField(null=False, default={})
    interval = IntegerField()
    created_at = DateTimeField(default=datetime.datetime.now)
    last_success_at = DateTimeField(null=True)
    next_time_at = DateTimeField(index=True, default=datetime.datetime.now)

    class Meta:
        indexes = (
            (('type', 'metadata'), True),
        )

    def __str__(self):
        return "[{}] {} - {}".format(self.created_at, self.id, self.type)

    @staticmethod
    def take():
        table = Job._meta.table_name
        job_id = db.execute_sql(
            ('SELECT j2.id FROM (SELECT * FROM {} as j ' +
             'WHERE j.next_time_at <= %s ORDER BY next_time_at) as j2 ' +
             'WHERE pg_try_advisory_lock(%s, j2.id) LIMIT 1').format(table),
            params=[datetime.datetime.now(), settings.JOB_LOCK_PREFIX]
        )

        job_result = job_id.fetchall()
        if not job_result:
            return None

        return Job.get_by_id(job_result[0][0])

    def release(self):
        db.execute_sql('SELECT pg_advisory_unlock(%s, %s)', [settings.JOB_LOCK_PREFIX, self.id])


class TopLevelCategory(BaseModel):
    id = IntegerField(primary_key=True)
    title = TextField(null=False)
    link = CharField()
    created_at = DateTimeField(default=datetime.datetime.now)


class Podcast(BaseModel):
    id = IntegerField(primary_key=True)
    itunes_title = TextField(null=False)
    itunes_link = TextField(null=False)
    category = ForeignKeyField(TopLevelCategory)
    category_page = IntegerField(null=False)
    category_letter = CharField(null=False)
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField(null=True)


class PodcastItunesLookup(BaseModel):
    id = IntegerField(primary_key=True)
    itunes_lookup = JSONField(null=True)
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField(null=True)


class PodcastRss(BaseModel):
    id = IntegerField(primary_key=True)
    rss = TextField(null=True)
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField(null=True)


db_models = [TopLevelCategory, Job, Podcast, PodcastRss, PodcastItunesLookup]


class Proxy():
    def __init__(self, proxy_info: dict):
        self._proxy_info = proxy_info

    def get_proxy_string(self):
        return "{type[0]}://{ip}:{port}".format(**self._proxy_info)

    @staticmethod
    def _get_set_key():
        return "S:PROXY_LIST"

    @staticmethod
    def get_by_ids(ids):
        values = redis.mget(map(lambda id: Proxy._get_redis_key(id.decode('utf-8')), ids))
        return list(map(lambda x: Proxy(json.loads(x)), values))

    @staticmethod
    def _get_redis_key(id):
        return "PROXY:{}".format(id)

    @staticmethod
    def get_random_proxy():
        id = redis.srandmember(Proxy._get_set_key())
        if id:
            proxies = Proxy.get_by_ids([id])
            return proxies[0] if proxies else None
        else:
            return None
