#!/usr/bin/env bash

arch=$1
docker_id=$2
docker_password=$3
docker_repo=$4
commit_id=$5

function build_version_test_images() {
  # 1~6 API number
  # 7 arch
  version_image=`./generate_version_image.sh \$1 \$2 \$3 \$4 \$5 \$6 | tail -n 1`
  docker push ${version_image}-${7}
  
  if [ ${7} == 'arm64' ]
  then
    docker manifest create ${version_image} ${version_image}-amd64 ${version_image}-arm64
    docker manifest push ${version_image}
  fi
}

# Build and get API information
if [ ${commit_id} != '' ]
then
  git clone https://github.com/longhorn/longhorn-engine.git --branch ${commit_id} --single-branch
else
  git clone https://github.com/longhorn/longhorn-engine.git
fi
sed -i "s/.*ARG DAPPER_HOST_ARCH=.*/ARG DAPPER_HOST_ARCH=${arch}/" longhorn-engine/Dockerfile.dapper
cd longhorn-engine
echo -en test >> README.md
git config --global user.email mock@gmail.com
git config --global user.name mock
git commit -a -m "make commit number diff"
sudo make build
base_image=$(sudo make package | grep "Successfully tagged longhornio/longhorn-engine:" | cut -d ' ' -f3)
echo $base_image

version=`docker run ${base_image} longhorn version --client-only`
export CLIAPIVersion=`echo $version|jq -r ".clientVersion.cliAPIVersion"`
export CLIAPIMinVersion=`echo $version|jq -r ".clientVersion.cliAPIMinVersion"`
export ControllerAPIVersion=`echo $version|jq -r ".clientVersion.controllerAPIVersion"`
export ControllerAPIMinVersion=`echo $version|jq -r ".clientVersion.controllerAPIMinVersion"`
export DataFormatVersion=`echo $version|jq -r ".clientVersion.dataFormatVersion"`
export DataFormatMinVersion=`echo $version|jq -r ".clientVersion.dataFormatMinVersion"`

# Build upgrade images
upgrade_image="${docker_repo}:upgrade-test.$CLIAPIVersion-$CLIAPIMinVersion"\
".$ControllerAPIVersion-$ControllerAPIMinVersion"\
".$DataFormatVersion-$DataFormatMinVersion"

docker login -u=${docker_id} -p=${docker_password}
image_info=($(docker images | grep "longhornio/longhorn-engine"))
image_id=${image_info[2]}
docker tag ${image_id} ${upgrade_image}-${arch}
docker push ${upgrade_image}-${arch}

if [ ${arch} == 'arm64' ]
then
  docker manifest create ${upgrade_image} ${upgrade_image}-amd64 ${upgrade_image}-arm64
  docker manifest push ${upgrade_image}
fi

# Build version images
git clone https://github.com/longhorn/longhorn-tests.git
cd longhorn-tests/manager/test_containers/compatibility

docker_repo=(${docker_repo////\\/})
sed -i "s/.*docker build -t longhornio\\/longhorn-test:\${version_tag} package*/docker build -t ${docker_repo}:\${version_tag}-${arch} package/" generate_version_image.sh
sed -i "s/.*echo longhornio\\/longhorn-test:\${version_tag}*/echo ${docker_repo}:\${version_tag}/" generate_version_image.sh
build_version_test_images $((CLIAPIVersion-1)) $((CLIAPIMinVersion-1)) $ControllerAPIVersion $ControllerAPIMinVersion $DataFormatVersion $DataFormatMinVersion $arch
build_version_test_images $((CLIAPIVersion+1)) $((CLIAPIMinVersion+1)) $ControllerAPIVersion $ControllerAPIMinVersion $DataFormatVersion $DataFormatMinVersion $arch
build_version_test_images $((CLIAPIMinVersion-1)) $((CLIAPIMinVersion-1)) $ControllerAPIVersion $ControllerAPIMinVersion $DataFormatVersion $DataFormatMinVersion $arch
build_version_test_images $CLIAPIVersion $CLIAPIMinVersion $ControllerAPIVersion $ControllerAPIMinVersion $DataFormatVersion $DataFormatMinVersion $arch
build_version_test_images $((CLIAPIVersion+1)) $((CLIAPIVersion+1)) $ControllerAPIVersion $ControllerAPIMinVersion $DataFormatVersion $DataFormatMinVersion $arch