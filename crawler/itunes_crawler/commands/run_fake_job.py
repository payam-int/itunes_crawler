import json

import click

from itunes_crawler.app import JobExecutor
from itunes_crawler.models2 import ScheduledJob, Session, ScheduledJobTypes


@click.command()
@click.argument("job_type")
@click.argument("id")
@click.argument("meta")
def run_job(job_type, id, meta):
    """ Runs a job with given classname """

    job_executor = JobExecutor.get()

    session = Session()
    job = ScheduledJob(
        type=ScheduledJobTypes[job_type],
        id=id,
        meta=json.loads(meta)
    )
    job_executor.execute(session, job)
    session.commit()


if __name__ == '__main__':
    run_job()
