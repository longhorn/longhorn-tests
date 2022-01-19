import paramiko
import subprocess
import yaml
import os
import pathlib

docker_id = "chanow"
docker_pwd = "tt2252"
docker_repo = "chanow/longhorn-engine"
docker_tag = "0119-test"

os.environ['TF_VAR_tf_workspace'] \
    = str(pathlib.Path(__file__).parent.absolute())
os.environ['TF_VAR_build_engine_aws_access_key'] \
    = "AKIAZKQ2ZGMOAKJCJC7Z"
os.environ['TF_VAR_build_engine_aws_secret_key'] \
    = "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"


def add_manifest():

    commands = 'docker login -u={0} -p={1};\
        docker manifest create {2}:{3} \\{2}:{3}-amd64 \\{2}:{3}-arm64;\
        docker manifest push {2}:{3}'\
            .format(docker_id, docker_pwd, docker_repo, docker_tag)
    print(commands)
    subprocess.run(commands, shell=True)


def build_test_engine():
    # arch : amd64 arm64
    build_docker(arch="amd64")
    build_docker(arch="arm64")
    add_manifest()


def build_docker(arch=None):

    os.environ['TF_VAR_build_engine_arch'] = arch

    if arch == "amd64":

        os.environ['TF_VAR_build_engine_aws_instance_type'] = 't2.xlarge'

    elif arch == "arm64":

        os.environ['TF_VAR_build_engine_aws_instance_type'] = 'a1.xlarge'

    subprocess.check_output("{}/scripts/build-engine.sh".format(
                            pathlib.Path(__file__).parent.absolute()))

    print("Start build {} engine image ...".format(arch))
    print("This may take awhile...")

    f = open("{}/config.yml".format(pathlib.Path(__file__).parent.absolute()))
    data = yaml.safe_load(f)
    ip = data['nodes'][0]['address']
    username = data['nodes'][0]['user']

    commands = 'git clone https://github.com/longhorn/longhorn-engine.git;\
            sed -i "s/.*ARG DAPPER_HOST_ARCH=.*/ARG DAPPER_HOST_ARCH={0}/" \
                longhorn-engine/Dockerfile.dapper;\
            cd longhorn-engine;\
            echo -en test >> README.md;\
            git config --global user.email "moke@gmail.com";\
            git config --global user.name "moke";\
            git commit -a -m "make commit number diff";\
            sudo usermod -aG docker ubuntu;\
            sudo make build;\
            sudo make package'.format(arch)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, username=username, key_filename=os.path.expanduser(
                    os.path.join("~", ".ssh", "id_rsa")), timeout=1500)

    stdin, stdout, stderr = client.exec_command(commands)
    output = stdout.readlines()
    err = stderr.readlines()
    print(err)

    stdin, stdout, stderr = client.exec_command("docker login -u={0} -p={1}; docker images".format(docker_id, docker_pwd))
    output = stdout.readlines()
    for line in output:
        if "longhornio/longhorn-engine" in line:
            image_id = line.split()[2]
            break

    print("Pushing {} engine docker image ...".format(arch))
    commands = 'docker tag {0} {1}:{2}-{3};\
                docker push {1}:{2}-{3}'.format(
                    image_id, docker_repo, docker_tag, arch)

    stdin, stdout, stderr = client.exec_command(commands, get_pty=True)
    output = stdout.readlines()
    #print(output)

    print("Pushing {} engine docker image done.".format(arch))
    client.close()

    subprocess.check_output("{}/scripts/cleanup.sh".format(
                            pathlib.Path(__file__).parent.absolute()))


if __name__ == "__main__":

    build_test_engine()
