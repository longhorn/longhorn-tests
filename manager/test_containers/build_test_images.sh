#!/bin/bash

set -e

cd compatibility
img1=`./generate_version_image.sh 4 4 3 3 1 1 1 1 | tail -n 1`
img2=`./generate_version_image.sh 2 2 3 3 1 1 1 1| tail -n 1`
img3=`./generate_version_image.sh 3 3 4 4 1 1 1 1 | tail -n 1`
img4=`./generate_version_image.sh 3 3 2 2 1 1 1 1 | tail -n 1`
img5=`./generate_version_image.sh 3 3 3 3 1 1 1 1 | tail -n 1`

cd ..
cd upgrade
live_upgrade_images=`./generate_live_upgrade_image.sh | tail -n 2`

echo build done
echo The commands for push:
echo docker push $img1
echo docker push $img2
echo docker push $img3
echo docker push $img4
echo docker push $img5
for live_upgrade_image in ${live_upgrade_images[@]}
do
echo docker push ${live_upgrade_image}
done

pushd baseimage &>/dev/null
./generate.sh
popd &>/dev/null