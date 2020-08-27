#!/bin/bash

set -e

cd compatibility
img1=`./generate_version_image.sh 5 5 3 3 1 1 | tail -n 1`
img2=`./generate_version_image.sh 2 2 3 3 1 1 | tail -n 1`
img3=`./generate_version_image.sh 4 3 4 4 1 1 | tail -n 1`
img4=`./generate_version_image.sh 4 3 2 2 1 1 | tail -n 1`
img5=`./generate_version_image.sh 4 3 3 3 1 1 | tail -n 1`

cd ..
cd upgrade
live_upgrade_image=`./generate_live_upgrade_image.sh | tail -n 1`

echo build done
echo The commands for push:
echo docker push $img1
echo docker push $img2
echo docker push $img3
echo docker push $img4
echo docker push $img5
echo docker push $live_upgrade_image

pushd baseimage &>/dev/null
./generate.sh
popd &>/dev/null