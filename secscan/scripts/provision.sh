#!/bin/bash 

DOCKER_VERSION=20.10

systemctl stop apt-daily.service
systemctl stop apt-daily-upgrade.service
systemctl kill --kill-who=all apt-daily.service
systemctl kill --kill-who=all apt-daily-upgrade.service

# wait until `apt-get updated` has been killed
while ! (systemctl list-units --all apt-daily.service | egrep -q '(dead|failed)')
do
  sleep 1;
done
while ! (systemctl list-units --all apt-daily-upgrade.service | egrep -q '(dead|failed)')
do
  sleep 1;
done

apt-get update && apt-get install -y build-essential git

curl https://releases.rancher.com/install-docker/${DOCKER_VERSION}.sh | sh
