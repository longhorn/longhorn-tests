def imageName = "${JOB_NAME}${env.BUILD_NUMBER}"

node {

    checkout(
       [$class: 'GitSCM',
        //branches: [[name: 'longhorn-56']],
        userRemoteConfigs: [[url: 'https://github.com/rancher/longhorn-tests.git']]]
    )

    stage('build') {
        sh "./scripts/build.sh"
        sh "docker run -itd --name ${JOB_NAME}${BUILD_NUMBER} --env TF_VAR_do_token=${TF_VAR_do_token} --env TF_VAR_tf_workspace=${TF_VAR_tf_workspace} ${imageName}"
    }

    try {
        stage ('terraform') {
            sh  " docker exec ${JOB_NAME}${BUILD_NUMBER} ${TF_VAR_tf_workspace}/scripts/terraform-setup.sh"
        }

        stage ('rke') {
            sh  " docker exec ${JOB_NAME}${BUILD_NUMBER} ${TF_VAR_tf_workspace}/scripts/rke-setup.sh"
        }

        stage ('longhorn setup & tests') {
            sh  " docker exec ${JOB_NAME}${BUILD_NUMBER} ${TF_VAR_tf_workspace}/scripts/longhorn-setup.sh"
        }
        stage ('report generation') {
            sh 'docker cp ${JOB_NAME}${BUILD_NUMBER}:/src/longhorn-tests/longhorn-test-junit-report.xml .'
            junit 'longhorn-test-junit-report.xml'
        }
    } finally {
        stage('releasing resources') {
            sh  " docker exec ${JOB_NAME}${BUILD_NUMBER} ${TF_VAR_tf_workspace}/scripts/cleanup.sh"
            sh "docker stop ${JOB_NAME}${BUILD_NUMBER}"
            sh "docker rm -v ${JOB_NAME}${BUILD_NUMBER}"
            sh "docker rmi ${imageName}"
     }
    }
}
