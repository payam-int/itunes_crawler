FROM python:3
WORKDIR /src/app/
ADD ./requirements.txt /src/app/
RUN pip install -r requirements.txt
ADD ./alembic.ini /src/app/
ADD ./itunes_crawler/ /src/app/itunes_crawler/

CMD [ "python", "-m", "itunes_crawler" ]
