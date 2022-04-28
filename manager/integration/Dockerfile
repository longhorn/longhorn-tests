FROM registry.suse.com/bci/python:3.9

ARG KUBECTL_VERSION=v1.17.0
ARG ARCH=amd64

RUN zypper ref -f
RUN zypper in -y vim-small nfs-client xfsprogs

RUN curl -sO https://storage.googleapis.com/kubernetes-release/release/$KUBECTL_VERSION/bin/linux/${ARCH}/kubectl && \
    mv kubectl /usr/local/bin/kubectl && \
    chmod +x /usr/local/bin/kubectl

ADD tests/requirements.txt .

RUN zypper in -y gcc python39-devel
RUN pip install -r requirements.txt

ADD . /integration
WORKDIR /integration/tests

ENTRYPOINT ["./run.sh"]
