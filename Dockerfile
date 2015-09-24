FROM python:2.7.7

RUN mkdir -p /opt/test
WORKDIR /opt/test

RUN apt-get -y update && apt-get -y install nginx supervisor

COPY requirements.txt /opt/test/
RUN pip install -r requirements.txt --index-url https://admin:password@pypi.local/simple/
RUN pip install --upgrade --pre test --index-url https://admin:password@pypi.local/simple/

COPY . /opt/test

RUN SECRET_KEY=notsecret python adminui/manage.py collectstatic --noinput

EXPOSE 80

CMD /usr/bin/supervisord -c /etc/supervisor/supervisord.conf -n
