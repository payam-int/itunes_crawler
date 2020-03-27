FROM python:3
WORKDIR /src/app/
ADD ./requirements.txt /src/app/
RUN pip install -r requirements.txt
ADD ./proxy_pool/ /src/app/proxy_pool/

CMD [ "python", "-m", "proxy_pool" ]
