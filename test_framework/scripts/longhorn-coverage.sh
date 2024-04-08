#!/usr/bin/env bash

set -x

source pipelines/utilities/kubeconfig.sh
source test_framework/scripts/longhorn-setup.sh

copy_go-cover-dir_from_all_longhorn-manager_pods() {
    local ITER=0
    local LONGHORN_MANAGER_PODS=`kubectl get pods -n longhorn-system -l app=longhorn-manager --no-headers -o custom-columns=":metadata.name"`
    for pod in ${LONGHORN_MANAGER_PODS}; do
        kubectl cp -n longhorn-system ${pod}:/go-cover-dir go-cover-dir-${ITER} -c longhorn-manager
        ITER=$(expr $ITER + 1)
    done

    mkdir -p go-cover-dir-merged
    go tool covdata merge -i=$(ls | grep go-cover-dir- | xargs echo | sed 's/ /,/g') -o go-cover-dir-merged
}

generate_text_profile_for_each_repo() {
    go tool covdata textfmt -i=go-cover-dir-merged -o longhorn-manager-profile.txt -pkg=github.com/longhorn/longhorn-manager/...
    go tool covdata textfmt -i=go-cover-dir-merged -o longhorn-engine-profile.txt -pkg=github.com/longhorn/longhorn-engine/...
    # go tool covdata textfmt -i=go-cover-dir-merged -o longhorn-spdk-engine-profile.txt -pkg=github.com/longhorn/longhorn-spdk-engine/...
    go tool covdata textfmt -i=go-cover-dir-merged -o longhorn-instance-manager-profile.txt -pkg=github.com/longhorn/longhorn-instance-manager/...
    go tool covdata textfmt -i=go-cover-dir-merged -o longhorn-share-manager-profile.txt -pkg=github.com/longhorn/longhorn-share-manager/...
    go tool covdata textfmt -i=go-cover-dir-merged -o backing-image-manager-profile.txt -pkg=github.com/longhorn/backing-image-manager/...
}

generate_html_profiles_for_each_repo() {
    CUSTOM_LONGHORN_MANAGER_BRANCH=${CUSTOM_LONGHORN_MANAGER_BRANCH:-"master"}
    CUSTOM_LONGHORN_ENGINE_BRANCH=${CUSTOM_LONGHORN_ENGINE_BRANCH:-"master"}
    # CUSTOM_LONGHORN_SPDK_ENGINE_BRANCH=${CUSTOM_LONGHORN_SPDK_ENGINE_BRANCH:-"master"}
    CUSTOM_LONGHORN_INSTANCE_MANAGER_BRANCH=${CUSTOM_LONGHORN_INSTANCE_MANAGER_BRANCH:-"master"}
    CUSTOM_LONGHORN_SHARE_MANAGER_BRANCH=${CUSTOM_LONGHORN_SHARE_MANAGER_BRANCH:-"master"}
    CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_BRANCH=${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_BRANCH:-"master"}

    git clone https://github.com/longhorn/longhorn-manager -b ${CUSTOM_LONGHORN_MANAGER_BRANCH}
    git clone https://github.com/longhorn/longhorn-engine -b ${CUSTOM_LONGHORN_ENGINE_BRANCH}
    # git clone https://github.com/longhorn/longhorn-spdk-engine -b ${CUSTOM_LONGHORN_SPDK_ENGINE_BRANCH}
    git clone https://github.com/longhorn/longhorn-instance-manager -b ${CUSTOM_LONGHORN_INSTANCE_MANAGER_BRANCH}
    git clone https://github.com/longhorn/longhorn-share-manager -b ${CUSTOM_LONGHORN_SHARE_MANAGER_BRANCH}
    git clone https://github.com/longhorn/backing-image-manager -b ${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_BRANCH}

    cp longhorn-manager-profile.txt longhorn-manager/profile.txt
    cp longhorn-engine-profile.txt longhorn-engine/profile.txt
    # cp longhorn-spdk-engine-profile.txt longhorn-spdk-engine/profile.txt
    cp longhorn-instance-manager-profile.txt longhorn-instance-manager/profile.txt
    cp longhorn-share-manager-profile.txt longhorn-share-manager/profile.txt
    cp backing-image-manager-profile.txt backing-image-manager/profile.txt

    cd longhorn-manager && go tool cover -html=profile.txt -o ../longhorn-manager-profile.html && cd ..
    cd longhorn-engine && go tool cover -html=profile.txt -o ../longhorn-engine-profile.html && cd ..
    # cd longhorn-spdk-engine && go tool cover -html=profile.txt -o ../longhorn-spdk-engine-profile.html && cd ..
    cd longhorn-instance-manager && go tool cover -html=profile.txt -o ../longhorn-instance-manager-profile.html && cd ..
    cd longhorn-share-manager && go tool cover -html=profile.txt -o ../longhorn-share-manager-profile.html && cd ..
    cd backing-image-manager && go tool cover -html=profile.txt -o ../backing-image-manager-profile.html && cd ..
}

main() {
    set_kubeconfig

    # uninstall longhorn to write coverage data
    # the coverage data will be written when the program invokes os.Exit() or returns normally from main.main
    # ref: https://go.dev/doc/build-cover#panicprof
    uninstall_longhorn_by_chart

    # install longhorn again to copy coverage data from pods, so we don't need scp files from host
    install_longhorn_by_chart

    copy_go-cover-dir_from_all_longhorn-manager_pods
    generate_text_profile_for_each_repo
    generate_html_profiles_for_each_repo
}

main
