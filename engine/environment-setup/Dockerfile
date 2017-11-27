FROM ubuntu:16.04

RUN apt-get update && apt-get install -y python openssh-client curl python-pip
RUN pip install --upgrade pip google-api-python-client packet-python

RUN curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-119.0.0-linux-x86_64.tar.gz
RUN tar zxvf google-cloud-sdk-119.0.0-linux-x86_64.tar.gz
ENV CLOUDSDK_CORE_DISABLE_PROMPTS="1"
RUN ./google-cloud-sdk/install.sh
RUN ./google-cloud-sdk/bin/gcloud components update

ADD *.py ./

ENTRYPOINT ["python"]

