import subprocess
import time
import random
import sys
import threading
import time
from multiprocessing import Process, Manager, Array, current_process

subprocess.call("sudo iscsiadm -m node --logout", shell=True)
subprocess.call("sudo rm /dev/longhorn/vol*", shell=True)
subprocess.call("docker rm -fv `docker ps -a | grep rancher/longhorn | awk '{print $1}'`", shell=True)
subprocess.call("docker network rm longhorn-net", shell=True)
subprocess.call("docker network create --subnet=172.18.0.0/16 longhorn-net", shell=True)


DATA_LEN = 100 * 1024

def write_data(i, pattern):
  fd = open("/dev/longhorn/vol" + str(i), "r+")
  fd.write(bytearray([pattern]*DATA_LEN))
  fd.close()

def check_data(i, pattern):
  fd = open("/dev/longhorn/vol" + str(i), "r")
  data = fd.read(DATA_LEN)
  fd.close()
  assert ord(data[0]) == pattern
 
def create_snapshot(controller):
  return subprocess.Popen(("docker exec " + controller + " launch snapshot create").split(), stdout=subprocess.PIPE).communicate()[0].rstrip()

def revert_snapshot(snap, controller):
  subprocess.call("docker exec " + controller + " launch snapshot revert " + snap, shell = True)

def run_test(i, iterations):
  for iteration in xrange(iterations):
    print "i = " + str(i)
    replica1 = subprocess.Popen(("docker run -d --net longhorn-net --ip 172.18.1." + str(i) + \
      " --expose 9502-9504 -v /volume rancher/longhorn launch replica --listen 172.18.1." + str(i) + \
      ":9502 --size " + str(DATA_LEN) + " /volume").split(), stdout=subprocess.PIPE).communicate()[0].rstrip()
    replica2 = subprocess.Popen(("docker run -d --net longhorn-net --ip 172.18.2." + str(i) + \
      " --expose 9502-9504 -v /volume rancher/longhorn launch replica --listen 172.18.2." + str(i) + \
      ":9502 --size " + str(DATA_LEN) + " /volume").split(), stdout=subprocess.PIPE).communicate()[0].rstrip()
    controller = subprocess.Popen(("docker run -d --net longhorn-net --privileged -v /dev:/host/dev" + \
      " -v /proc:/host/proc rancher/longhorn launch controller --frontend tgt" + \
      " --replica tcp://172.18.1." + str(i) + ":9502 --replica tcp://172.18.2." + str(i) + \
      ":9502 vol" + str(i)).split(), stdout=subprocess.PIPE).communicate()[0].rstrip()
    print "replica1 = " + str(replica1)
    print "replica2 = " + str(replica2)
    print "controller = " + str(controller)
    time.sleep(3)
    pattern1 = int(255 * random.random())
    write_data(i, pattern1)
    check_data(i, pattern1)
    snap = create_snapshot(controller)
    pattern2 = int(255 * random.random())
    write_data(i, pattern2)
    check_data(i, pattern2)
    revert_snapshot(snap, controller)
    check_data(i, pattern1)
    subprocess.call("docker kill " + controller + " " + replica1 + " " + replica2, shell=True)

workers = []

for i in xrange(10):
  p = Process(target = run_test, args = (i + 1, 10))
  workers.append(p)
  p.start()


for p in workers:
  p.join()
