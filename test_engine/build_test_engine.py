import paramiko
import subprocess
import yaml
import os
import pathlib
import json
import time

docker_id = os.getenv("docker_id")
docker_pwd = os.getenv("docker_pwd")
docker_repo = os.getenv("docker_repo")

RETRY_INTERVAL = 0.5

os.environ['TF_VAR_tf_workspace'] \
    = str(pathlib.Path(__file__).parent.absolute())

# TF_VAR_build_engine_aws_access_key
# TF_VAR_build_engine_aws_secret_key


def get_image_names():

    global CLIAPIVersion
    global CLIAPIMinVersion
    global ControllerAPIVersion
    global ControllerAPIMinVersion
    global DataFormatVersion
    global DataFormatMinVersion
    global docker_tag

    version = subprocess.check_output("{}/scripts/get_version.sh".format(
                            pathlib.Path(__file__).parent.absolute()))

    version = json.loads(version)

    CLIAPIVersion = \
        str(version["clientVersion"]["cliAPIVersion"])
    CLIAPIMinVersion = \
        str(version["clientVersion"]["cliAPIMinVersion"])
    ControllerAPIVersion = \
        str(version["clientVersion"]["controllerAPIVersion"])
    ControllerAPIMinVersion = \
        str(version["clientVersion"]["controllerAPIMinVersion"])
    DataFormatVersion = \
        str(version["clientVersion"]["dataFormatVersion"])
    DataFormatMinVersion = \
        str(version["clientVersion"]["dataFormatMinVersion"])

    docker_tag = "{}-{}.{}-{}.{}-{}".format(
        CLIAPIVersion, CLIAPIMinVersion,
        ControllerAPIVersion, ControllerAPIMinVersion,
        DataFormatVersion, DataFormatMinVersion)

    version_tag1 = "{}-{}.{}-{}.{}-{}".format(
        int(CLIAPIMinVersion) - 1, int(CLIAPIMinVersion) - 1,
        ControllerAPIVersion, ControllerAPIMinVersion,
        DataFormatVersion, DataFormatMinVersion)

    version_tag2 = "{}-{}.{}-{}.{}-{}".format(
        int(CLIAPIVersion) + 1, int(CLIAPIVersion) + 1,
        ControllerAPIVersion, ControllerAPIMinVersion,
        DataFormatVersion, DataFormatMinVersion)

    upgrade_image = "{0}:upgrade-test.{1}".format(docker_repo, docker_tag)
    version_image1 = "{0}:version-test.{1}".format(docker_repo, version_tag1)
    version_image2 = "{0}:version-test.{1}".format(docker_repo, version_tag2)

    print(upgrade_image)
    print(version_image1)
    print(version_image2)

    return upgrade_image, version_image1, version_image2


def __exec_command(ip, username, commands):

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, username=username, key_filename=os.path.expanduser(
                    os.path.join("~", ".ssh", "id_rsa")), timeout=1500)

    stdin, stdout, stderr = client.exec_command(commands)

    while int(stdout.channel.recv_exit_status()) != 0:
        time.sleep(RETRY_INTERVAL)

    output = stdout.readlines()

    client.close()

    print(output)

    return output


def add_manifest(upgrade_image, version_image1, version_image2):

    # upgrade image
    commands = 'docker login -u={0} -p={1};\
        docker manifest create {2} \\{2}-amd64 \\{2}-arm64;\
        docker manifest push {2}'\
            .format(docker_id, docker_pwd, upgrade_image)
    print(commands)
    subprocess.run(commands, shell=True)

    # version image
    commands = '\
        docker manifest create {0} \\{0}-amd64 \\{0}-arm64;\
        docker manifest push {0}'\
            .format(version_image1)
    print(commands)
    subprocess.run(commands, shell=True)

    # version image
    commands = '\
        docker manifest create {0} \\{0}-amd64 \\{0}-arm64;\
        docker manifest push {0}'\
            .format(version_image2)
    print(commands)
    subprocess.run(commands, shell=True)


def generate_test_images():

    # arch : amd64 arm64
    upgrade_image, version_image1, version_image2 = get_image_names()
    build_images("amd64", upgrade_image, version_image1, version_image2)
    build_images("arm64", upgrade_image, version_image1, version_image2)
    add_manifest(upgrade_image, version_image1, version_image2)


def build_images(arch, upgrade_image, version_image1, version_image2):

    os.environ['TF_VAR_build_engine_arch'] = arch

    if arch == "amd64":

        os.environ['TF_VAR_build_engine_aws_instance_type'] = 't2.xlarge'

    elif arch == "arm64":

        os.environ['TF_VAR_build_engine_aws_instance_type'] = 'a1.xlarge'

    subprocess.check_output("{}/scripts/terraform_instance.sh".format(
                            pathlib.Path(__file__).parent.absolute()))

    f = open("{}/config.yml".format(pathlib.Path(__file__).parent.absolute()))
    data = yaml.safe_load(f)
    ip = data['nodes'][0]['address']
    username = data['nodes'][0]['user']
    f.close()

    # upgrade test image
    print("Start build {} upgrade test image ...".format(arch))
    print("This may take awhile...")

    commands = 'git clone https://github.com/longhorn/longhorn-engine.git;\
            sed -i "s/.*ARG DAPPER_HOST_ARCH=.*/ARG DAPPER_HOST_ARCH={0}/" \
                longhorn-engine/Dockerfile.dapper;\
            cd longhorn-engine;\
            echo -en test >> README.md;\
            git config --global user.email "mock@gmail.com";\
            git config --global user.name "mock";\
            git commit -a -m "make commit number diff";\
            sudo usermod -aG docker ubuntu;\
            sudo make build;\
            sudo make package'.format(arch)

    __exec_command(ip, username, commands)

    commands = "docker login -u={0} -p={1}; \
                docker images".format(docker_id, docker_pwd)

    output = __exec_command(ip, username, commands)

    for line in output:
        if "longhornio/longhorn-engine" in line:
            image_id = line.split()[2]
            break

    print("Pushing {} upgrade test image ...".format(arch))

    commands = 'docker tag {0} {1}-{2};\
                docker push {1}-{2}'.format(
                    image_id, upgrade_image, arch)

    __exec_command(ip, username, commands)

    print("Pushing {} upgrade test docker image done.".format(arch))

    # version test image
    print("Start build {} version test image ...".format(arch))
    print("This may take awhile...")

    # remove sed part after really use longhon-test repo
    commands = 'git clone https://github.com/longhorn/longhorn-tests.git;\
            cd ~/longhorn-tests/manager/test_containers/compatibility;\
            sed -i "s/.*docker build -t longhornio\\/longhorn-test.*/\
                docker build -t {0}-{1} package/" generate_version_image.sh;\
            '.format(version_image1.replace('/', '\\/'), arch)
    __exec_command(ip, username, commands)

    commands = 'cd ~/longhorn-tests/manager/test_containers/compatibility;\
            ./generate_version_image.sh {0} {1} {2} {3} {4} {5}'\
                .format(int(CLIAPIMinVersion) - 1, int(CLIAPIMinVersion) - 1,
                        ControllerAPIVersion, ControllerAPIMinVersion,
                        DataFormatVersion, DataFormatMinVersion)
    __exec_command(ip, username, commands)

    print("Pushing {} version test image ...".format(arch))
    commands = 'docker push {}-{}'.format(version_image1, arch)
    __exec_command(ip, username, commands)

    commands = 'rm -rf longhorn-tests'
    __exec_command(ip, username, commands)

    # remove sed part after really use longhon-test repo
    commands = 'git clone https://github.com/longhorn/longhorn-tests.git;\
            cd ~/longhorn-tests/manager/test_containers/compatibility;\
            sed -i "s/.*docker build -t longhornio\\/longhorn-test.*/\
                docker build -t {0}-{1} package/" generate_version_image.sh;\
            '.format(version_image2.replace('/', '\\/'), arch)
    __exec_command(ip, username, commands)

    commands = 'cd ~/longhorn-tests/manager/test_containers/compatibility;\
            ./generate_version_image.sh {0} {1} {2} {3} {4} {5}'\
                .format(int(CLIAPIVersion) + 1, int(CLIAPIVersion) + 1,
                        ControllerAPIVersion, ControllerAPIMinVersion,
                        DataFormatVersion, DataFormatMinVersion)
    __exec_command(ip, username, commands)

    print("Pushing {} version test image ...".format(arch))
    commands = 'docker push {}-{}'.format(version_image2, arch)
    __exec_command(ip, username, commands)

    subprocess.check_output("{}/scripts/cleanup.sh".format(
                            pathlib.Path(__file__).parent.absolute()))


if __name__ == "__main__":

    generate_test_images()
