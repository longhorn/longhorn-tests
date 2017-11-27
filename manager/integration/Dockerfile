FROM python:2.7.14-stretch

RUN apt-get update && \
    apt-get install -y vim-tiny

ADD . /integration
WORKDIR /integration/tests

RUN pip install -r requirements.txt

ENTRYPOINT ["./run.sh"]
