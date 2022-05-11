#!/bin/bash

set -e

# (1) install docker

sudo apt-get update
sudo apt-get install -y docker.io

# (2) install letsencrypt certbot tool

sudo snap install core
sudo snap refresh core
sudo snap install --classic certbot

# (3) create certificates

sudo certbot certonly --standalone -d ${registry_url} --non-interactive --agree-tos -m yang.chiu@suse.com
mkdir "${PWD}/certs"
sudo cp "/etc/letsencrypt/live/${registry_url}/fullchain.pem" "${PWD}/certs/public.crt"
sudo cp "/etc/letsencrypt/live/${registry_url}/privkey.pem" "${PWD}/certs/private.key"

# (4) create basic auth

mkdir "${PWD}/auth"
sudo docker run --entrypoint htpasswd httpd:2 -Bbn ${registry_username} ${registry_password} > "${PWD}/auth/htpasswd"

# (5) run registry container with certificates and auth

sudo docker run -d --name registry \
                -v "${PWD}/auth":/auth \
                -e REGISTRY_AUTH=htpasswd \
                -e REGISTRY_AUTH_HTPASSWD_REALM="Registry Realm" \
                -e REGISTRY_AUTH_HTPASSWD_PATH=/auth/htpasswd \
                -v "${PWD}/certs":/certs \
                -e REGISTRY_HTTP_ADDR=0.0.0.0:443 \
                -e REGISTRY_HTTP_TLS_CERTIFICATE=/certs/public.crt \
                -e REGISTRY_HTTP_TLS_KEY=/certs/private.key \
                -p 443:443 \
                registry:2

# (6) test registry with docker login command

sudo docker login -u ${registry_username} -p ${registry_password} ${registry_url}

# (7) pull longhorn images into registry

wget https://raw.githubusercontent.com/longhorn/longhorn/${longhorn_version}/deploy/longhorn-images.txt
wget https://raw.githubusercontent.com/longhorn/longhorn/${longhorn_version}/scripts/save-images.sh
wget https://raw.githubusercontent.com/longhorn/longhorn/${longhorn_version}/scripts/load-images.sh
chmod +x "${PWD}/save-images.sh"
chmod +x "${PWD}/load-images.sh"
sudo "${PWD}/save-images.sh" --image-list "${PWD}/longhorn-images.txt" --images "${PWD}/longhorn-images.tar.gz"
sudo "${PWD}/load-images.sh" --image-list "${PWD}/longhorn-images.txt" --images "${PWD}/longhorn-images.tar.gz" --registry ${registry_url}

# (8) test list all images in registry

curl -X GET -u ${registry_username}:${registry_password} https://${registry_url}/v2/_catalog
