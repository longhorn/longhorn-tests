

export docker_id="chanow"
export docker_pwd="tt2252"
export docker_repo="chanow/longhorn-engine"
export docker_tag="20220119"

export TF_VAR_tf_workspace="$(dirname $(dirname -- $(readlink -fn -- "$0")))"
export TF_VAR_build_engine_aws_access_key="AKIAZKQ2ZGMOFDY53S2J"
export TF_VAR_build_engine_aws_secret_key="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"

export TF_VAR_build_engine_arch="amd64"
export TF_VAR_build_engine_aws_instance_type="t2.xlarge"


export TF_VAR_build_engine_arch="arm64"
export TF_VAR_build_engine_aws_instance_type="a1.xlarge"