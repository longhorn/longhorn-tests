#!/bin/bash

if [ $# -lt 6 ]
then
	echo not enough arguments
	exit
fi

export CLIAPIVersion=$1
export CLIAPIMinVersion=$2
export ControllerAPIVersion=$3
export ControllerAPIMinVersion=$4
export DataFormatVersion=$5
export DataFormatMinVersion=$6

version_tag="version-test.${CLIAPIVersion}-${CLIAPIMinVersion}"\
".${ControllerAPIVersion}-${ControllerAPIMinVersion}"\
".${DataFormatVersion}-${DataFormatMinVersion}"

export Version="\"${version_tag}\""

yaml=`envsubst < template.yaml`
echo -e "#!/bin/sh\necho '$yaml'" > package/longhorn
echo -e "#!/bin/sh\necho status: SERVING" > package/grpc_health_probe
echo -e "#!/bin/sh\nsleep infinity" > package/engine-manager
echo -e "#!/bin/sh\nsleep infinity" > package/longhorn-instance-manager
chmod a+x package/longhorn package/grpc_health_probe package/engine-manager package/longhorn-instance-manager

docker build -t longhornio/longhorn-test:${version_tag} package/
echo
echo longhornio/longhorn-test:${version_tag}
