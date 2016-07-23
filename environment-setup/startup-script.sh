touch /startup.log

curl -sSL --retry 10 --retry-delay 10 https://releases.rancher.com/install-docker/1.10.3.sh| sh >> /startup.log 2>&1

if command -v systemctl > /dev/null; then
    echo "Starting docker..."  >> /startup.log 2>&1
    systemctl stop docker >> /startup.log 2>&1
    sleep 10
    systemctl start docker >> /startup.log 2>&1
fi

sleep 5
docker run -d -p 8080:8080  --privileged rancher/server:v1.1.1 >> /startup.log 2>&1
