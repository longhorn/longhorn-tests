FROM python:2.7.14-stretch

RUN apt-get update && \
    apt-get install -y vim-tiny nfs-common

ADD tests/requirements.txt .
RUN pip install -r requirements.txt

ADD . /integration
WORKDIR /integration/tests

ENTRYPOINT ["./run.sh"]
