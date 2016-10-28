import subprocess
import time
import random
import sys
import threading
import time
import os
from os import path
import stat

from multiprocessing import Process, Manager, Array, current_process, Lock

subprocess.call("sudo iscsiadm -m node --logout", shell=True)
subprocess.call("sudo rm /dev/longhorn/vol*", shell=True)
#subprocess.call("docker rm -fv `docker ps -a | grep rancher/longhorn | awk '{print $1}'`", shell=True)
subprocess.call("docker rm -fv `docker ps -qa`", shell=True)
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

def wait_for_dev_ready(i, iteration):
  dev = "/dev/longhorn/vol" + str(i)
  init_time = time.time()
  while time.time() - init_time < 20:
    if os.path.exists(dev):
      mode = os.stat(dev).st_mode
      if stat.S_ISBLK(mode):
        print "iteration = " + str(iteration) + " thread = " + str(i) + " Device ready after " + str(time.time() - init_time) + " seconds"
        return
    time.sleep(0.02)
  print("FAIL TO WAIT FOR DEVICE READY")
  return

def run_test(thread, iterations, lock):
  for iteration in xrange(iterations):
    replica1 = subprocess.Popen(("docker run -d --name r1-" + str(iteration) + "-" + str(thread) + \
      " --net longhorn-net --ip 172.18.1." + str(thread) + \
      " --expose 9502-9504 -v /volume rancher/longhorn launch replica --listen 172.18.1." + str(thread) + \
      ":9502 --size " + str(DATA_LEN) + " /volume").split(), stdout=subprocess.PIPE).communicate()[0].rstrip()
    replica2 = subprocess.Popen(("docker run -d --name r2-" + str(iteration) + "-" + str(thread) + \
      " --net longhorn-net --ip 172.18.2." + str(thread) + \
      " --expose 9502-9504 -v /volume rancher/longhorn launch replica --listen 172.18.2." + str(thread) + \
      ":9502 --size " + str(DATA_LEN) + " /volume").split(), stdout=subprocess.PIPE).communicate()[0].rstrip()
    print "iteration = " + str(iteration) + " thread = " + str(thread) + " replica1 = " + str(replica1)
    print "iteration = " + str(iteration) + " thread = " + str(thread) + " replica2 = " + str(replica2)
    lock.acquire()
    try:
      controller = subprocess.Popen(("docker run -d --name c-" + str(iteration) + "-" + str(thread) + \
        " --net longhorn-net --privileged -v /dev:/host/dev" + \
        " -v /proc:/host/proc rancher/longhorn launch controller --frontend tgt" + \
        " --replica tcp://172.18.1." + str(thread) + ":9502 --replica tcp://172.18.2." + str(thread) + \
        ":9502 vol" + str(thread)).split(), stdout=subprocess.PIPE).communicate()[0].rstrip()
    finally:
      lock.release()
    print "iteration = " + str(iteration) + " thread = " + str(thread) + " controller = " + str(controller)
    wait_for_dev_ready(thread, iteration)
    pattern1 = int(255 * random.random())
    write_data(thread, pattern1)
    check_data(thread, pattern1)
    snap = create_snapshot(controller)
    pattern2 = int(255 * random.random())
    write_data(thread, pattern2)
    check_data(thread, pattern2)
    lock.acquire()
    try:
      revert_snapshot(snap, controller)
    finally:
      lock.release()
    wait_for_dev_ready(thread, iteration)
    check_data(thread, pattern1)
    subprocess.call("docker stop " + controller + " " + replica1 + " " + replica2, shell=True)
    subprocess.call("docker rm -fv " + controller + " " + replica1 + " " + replica2, shell=True)

workers = []

lock = Lock()

for thread in xrange(20):
  p = Process(target = run_test, args = (thread + 1, 1000, lock))
  workers.append(p)
  p.start()


for p in workers:
  p.join()
