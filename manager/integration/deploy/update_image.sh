#!/bin/bash

set -e

cd $(dirname $0)/..

files=`find ./deploy/ |grep yaml |sort`
project="rancher\/longhorn-manager-test"

latest=`cat bin/latest_image`
echo latest image ${latest}

escaped_latest=${latest//\//\\\/}

for f in $files
do
	sed -i "s/image\:\ ${project}:.*/image\:\ ${escaped_latest}/g" $f
done
