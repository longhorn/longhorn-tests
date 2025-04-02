FROM registry.suse.com/bci/python:3.11

ARG TARGETPLATFORM
RUN if [ "$TARGETPLATFORM" != "linux/amd64" ] && [ "$TARGETPLATFORM" != "linux/arm64" ]; then \
    echo "Error: Unsupported TARGETPLATFORM: $TARGETPLATFORM" && \
    exit 1; \
    fi
ENV ARCH ${TARGETPLATFORM#linux/}

ARG KUBECTL_VERSION=v1.30.0
ARG YQ_VERSION=v4.24.2
ARG TERRAFORM_VERSION=1.3.5

RUN zypper ref -f
RUN zypper in -y vim-small nfs-client xfsprogs e2fsprogs util-linux-systemd gcc python311-devel gawk java-21-openjdk tar awk gzip wget unzip && \
    rm -rf /var/cache/zypp/*

RUN curl -sO https://storage.googleapis.com/kubernetes-release/release/$KUBECTL_VERSION/bin/linux/${ARCH}/kubectl && \
    mv kubectl /usr/local/bin/kubectl && \
    chmod +x /usr/local/bin/kubectl && \
    curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 && \
    chmod 700 get_helm.sh && \
    ./get_helm.sh && \
    wget -q "https://github.com/mikefarah/yq/releases/download/${YQ_VERSION}/yq_linux_${ARCH}" && \
    mv yq_linux_${ARCH} /usr/local/bin/yq && \
    chmod +x /usr/local/bin/yq && \
    curl -L https://github.com/jonelo/jacksum/releases/download/v3.4.0/jacksum-3.4.0.jar --output /jacksum.jar && \
    wget -q https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
    unzip terraform_${TERRAFORM_VERSION}_linux_amd64.zip && rm terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
    mv terraform /usr/bin/terraform && \
    chmod +x /usr/bin/terraform

ADD e2e /e2e
WORKDIR /e2e

ADD pipelines ./pipelines

RUN pip install -r requirements.txt

ENTRYPOINT ["./run.sh"]
