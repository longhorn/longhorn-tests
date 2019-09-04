#!/bin/bash

# make sure IMAGE wasn't used by any releases
IMAGE="longhornio/longhorn-engine:live-upgrade-2-2-1"

version=`docker run $IMAGE longhorn version --client-only`
echo Image version output: $version

CLIAPIVersion=`echo $version|jq -r ".clientVersion.cliAPIVersion"`
CLIAPIMinVersion=`echo $version|jq -r ".clientVersion.cliAPIMinVersion"`
ControllerAPIVersion=`echo $version|jq -r ".clientVersion.controllerAPIVersion"`
ControllerAPIMinVersion=`echo $version|jq -r ".clientVersion.controllerAPIMinVersion"`
DataFormatVersion=`echo $version|jq -r ".clientVersion.dataFormatVersion"`
DataFormatMinVersion=`echo $version|jq -r ".clientVersion.dataFormatMinVersion"`

test_image="longhornio/longhorn-test:upgrade-test.${CLIAPIVersion}-${CLIAPIMinVersion}"\
".${ControllerAPIVersion}-${ControllerAPIMinVersion}"\
".${DataFormatVersion}-${DataFormatMinVersion}"

docker tag $IMAGE $test_image
docker push $test_image

echo
echo $test_image
