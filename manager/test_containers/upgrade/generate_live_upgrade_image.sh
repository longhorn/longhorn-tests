#!/bin/bash

# make sure IMAGE wasn't used by any releases
# The 2nd image's InstanceManagerAPIVersion should be current version + 1
test_images=()
IMAGES=("shuowu/longhorn-engine:test1" "shuowu/longhorn-engine:test2")
for(( i=0;i<${#IMAGES[@]};i++))
do
version=`docker run ${IMAGES[i]} longhorn version --client-only`
echo Image version output: $version
echo
CLIAPIVersion=`echo $version|jq -r ".clientVersion.cliAPIVersion"`
CLIAPIMinVersion=`echo $version|jq -r ".clientVersion.cliAPIMinVersion"`
ControllerAPIVersion=`echo $version|jq -r ".clientVersion.controllerAPIVersion"`
ControllerAPIMinVersion=`echo $version|jq -r ".clientVersion.controllerAPIMinVersion"`
DataFormatVersion=`echo $version|jq -r ".clientVersion.dataFormatVersion"`
DataFormatMinVersion=`echo $version|jq -r ".clientVersion.dataFormatMinVersion"`
InstanceManagerAPIVersion=`echo $version|jq -r ".clientVersion.instanceManagerAPIVersion"`
InstanceManagerAPIMinVersion=`echo $version|jq -r ".clientVersion.instanceManagerAPIMinVersion"`

test_images[i]="longhornio/longhorn-test:upgrade-test.${CLIAPIVersion}-${CLIAPIMinVersion}"\
".${ControllerAPIVersion}-${ControllerAPIMinVersion}"\
".${DataFormatVersion}-${DataFormatMinVersion}"\
".${InstanceManagerAPIVersion}-${InstanceManagerAPIMinVersion}"

docker tag ${IMAGES[i]} ${test_images[i]}
docker push ${test_images[i]}
echo
done

for image in ${test_images[@]}
do
echo $image
done