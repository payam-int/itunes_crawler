import datetime
import enum

from sqlalchemy import Column, Enum, String, JSON, DateTime, create_engine, asc, Integer
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session as ISession
from sqlalchemy_dict import BaseModel

from itunes_crawler import settings

engine = create_engine(
    "postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}".format(**settings.POSTGRES),
    echo=True)
Base = declarative_base(cls=BaseModel)
Session = sessionmaker(bind=engine, autocommit=False)


class ScheduledJobTypes(enum.Enum):
    TOP_LEVEL_CATEGORIES = 'TOP_LEVEL_CATEGORIES'
    CATEGORY_LETTER = 'CATEGORY_LETTER'
    PODCAST_LOOKUP = 'PODCAST_LOOKUP'
    PODCAST_RSS = 'PODCAST_RSS'


class ScheduledJob(Base):
    __tablename__ = 'scheduled_jobs'

    type = Column(Enum(ScheduledJobTypes), primary_key=True)
    id = Column(String, primary_key=True)
    meta = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    next_time_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    last_success_at = Column(DateTime, nullable=True)
    failure_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, onupdate=datetime.datetime.utcnow)

    @staticmethod
    def take(session: ISession, count=1):
        assert session.transaction is not None

        return session \
                   .query(ScheduledJob) \
                   .filter(ScheduledJob.next_time_at < datetime.datetime.now()) \
                   .filter(ScheduledJob.finished_at == None) \
                   .order_by(asc(ScheduledJob.next_time_at)) \
                   .limit(count) \
                   .with_for_update(of=ScheduledJob, skip_locked=True)[:]

    def get_insert_query(self):
        return insert(ScheduledJob).values(**self.to_dict()).on_conflict_do_nothing()

    def success(self, interval):
        self.last_success_at = datetime.datetime.utcnow()
        self.next_time_at = datetime.datetime.utcnow() + interval

    def fail(self):
        self.failure_at = datetime.datetime.utcnow()
        self.next_time_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)


class ItunesTopLevelCategory(Base):
    __tablename__ = 'itunes_top_level_categories'
    itunes_id = Column(String, primary_key=True)
    title = Column(String)
    link = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.datetime.utcnow)


class ItunesListPodcast(Base):
    __tablename__ = 'itunes_list_podcast'

    itunes_id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    link = Column(String, nullable=False)
    category_page = Column(Integer, nullable=False)
    category_letter = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.datetime.utcnow)


class ItunesPodcastLookup(Base):
    __tablename__ = 'itunes_podcast_lookup'

    itunes_id = Column(String, primary_key=True)
    itunes_lookup = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.datetime.utcnow)


class ItunesPodcastRss(Base):
    __tablename__ = 'itunes_podcast_rss'

    itunes_id = Column(String, primary_key=True)
    rss = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.datetime.utcnow)
