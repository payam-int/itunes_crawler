import datetime
import logging
import signal

import peewee_extra_fields
from peewee import PostgresqlDatabase, Model, CharField, TextField, DateTimeField, IntegerField, AutoField, \
    ForeignKeyField, Field
from playhouse.postgres_ext import JSONField

from itunes_crawler import settings

logger = logging.getLogger('models')
db = PostgresqlDatabase(settings.POSTGRES['database'], host=settings.POSTGRES['host'],
                        port=settings.POSTGRES['port'], user=settings.POSTGRES['user'],
                        password=settings.POSTGRES['password'], autorollback=True,
                        field_types=peewee_extra_fields.FIELD_TYPES, thread_safe=True)

logger.info("Connected to database...")


def close_db():
    logger.info("Closing the database connection...")
    db.close()


signal.signal(signal.SIGTERM, close_db)
signal.signal(signal.SIGINT, close_db)


class XMLField(Field):
    field_type = 'xml'


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
    next_time_at = DateTimeField(index=True, default=datetime.datetime.now)

    class Meta:
        indexes = (
            ('type', 'metadata', True)
        )

    def __str__(self):
        return "[{}] {} - {}".format(self.created_at, self.id, self.type)

    @staticmethod
    def take():
        sorted_keys = [key.column_name for key in Job._meta.sorted_fields]
        query_keys = ['j2.{0}'.format(key) for key in sorted_keys]
        table = Job._meta.table_name
        job_data = db.execute_sql(
            ('SELECT {} FROM (SELECT * FROM {} as j ' +
             'WHERE j.next_time_at <= %s ORDER BY next_time_at) as j2 ' +
             'WHERE pg_try_advisory_lock(%s, j2.id) LIMIT 1').format(",".join(query_keys), table),
            params=[datetime.datetime.now(), settings.JOB_LOCK_PREFIX]
        )

        job_result = job_data.fetchall()
        if not job_result:
            return None

        fields = dict(zip(sorted_keys, job_result[0]))
        return Job(**fields)

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
    itunes_lookup = JSONField(null=True)
    rss = XMLField(null=True)
    category = ForeignKeyField(TopLevelCategory)
    category_page = IntegerField(null=False)
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField(null=True)


db_models = [TopLevelCategory, Job, Podcast]
