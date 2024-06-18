# syntax=docker/dockerfile:1.7.0

FROM registry.suse.com/bci/python:3.9

ARG TARGETPLATFORM
RUN if [ "$TARGETPLATFORM" != "linux/amd64" ] && [ "$TARGETPLATFORM" != "linux/arm64" ]; then \
    echo "Error: Unsupported TARGETPLATFORM: $TARGETPLATFORM" && \
    exit 1; \
    fi
ENV ARCH ${TARGETPLATFORM#linux/}

ARG KUBECTL_VERSION=v1.17.0

RUN zypper ref -f
RUN zypper in -y vim-small nfs-client xfsprogs e2fsprogs util-linux-systemd gcc python39-devel gawk java-11-openjdk && \
    rm -rf /var/cache/zypp/*

RUN curl -sO https://storage.googleapis.com/kubernetes-release/release/$KUBECTL_VERSION/bin/linux/${ARCH}/kubectl && \
    mv kubectl /usr/local/bin/kubectl && \
    chmod +x /usr/local/bin/kubectl

RUN curl -L https://github.com/jonelo/jacksum/releases/download/v3.4.0/jacksum-3.4.0.jar --output /jacksum.jar

ADD tests/requirements.txt .
RUN pip install -r requirements.txt

ADD . /integration
WORKDIR /integration/tests

ENTRYPOINT ["./run.sh"]
