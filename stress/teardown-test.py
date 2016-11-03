import subprocess
import time
import random
import sys
import threading
import time
import os
import directio
import mmap
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

PAGE_SIZE = 4096

def readat_direct(dev, offset, length):
    pg = offset / PAGE_SIZE
    in_page_offset = offset % PAGE_SIZE
    # either read less than a page, or whole pages
    if in_page_offset != 0:
        assert pg == (offset + length - 1) / PAGE_SIZE
        to_read = PAGE_SIZE
    else:
        assert length % PAGE_SIZE == 0
        to_read = length
    pg_offset = pg * PAGE_SIZE

    f = os.open(dev, os.O_DIRECT | os.O_RDONLY)
    try:
        os.lseek(f, pg_offset, os.SEEK_SET)
        ret = directio.read(f, to_read)
    finally:
        os.close(f)
    return ret[in_page_offset: in_page_offset + length]


def writeat_direct(dev, offset, data):
    pg = offset / PAGE_SIZE
    # don't support across page write
    assert pg == (offset + len(data) - 1) / PAGE_SIZE
    pg_offset = pg * PAGE_SIZE

    f = os.open(dev, os.O_DIRECT | os.O_RDWR)
    m = mmap.mmap(-1, PAGE_SIZE)
    try:
        os.lseek(f, pg_offset, os.SEEK_SET)
        pg_data = readat_direct(dev, pg_offset, PAGE_SIZE)
        m.write(pg_data)
        m.seek(offset % PAGE_SIZE)
        m.write(data)
        ret = directio.write(f, m)
    finally:
        m.close()
        os.close(f)
    return ret

def write_data(i, pattern):
  writeat_direct("/dev/longhorn/vol" + str(i), 0, str(chr(pattern))*PAGE_SIZE)

def check_data(i, pattern):
  data = readat_direct("/dev/longhorn/vol" + str(i), 0, PAGE_SIZE)
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
