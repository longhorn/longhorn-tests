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
import datetime

from multiprocessing import Process, Manager, Array, current_process, Lock

subprocess.call("sudo iscsiadm -m node --logout", shell=True)
subprocess.call("sudo rm /dev/longhorn/vol*", shell=True)
subprocess.call("docker rm -fv `docker ps -qa`", shell=True)
subprocess.call("docker network rm longhorn-net", shell=True)
subprocess.call("docker network create --subnet=172.18.0.0/16 longhorn-net", shell=True)

NUM_PAGES = 1024

PAGE_SIZE = 256 * 4096

DATA_LEN = NUM_PAGES * PAGE_SIZE

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
    except OSError as e:
        print "%s: encounter error in readat_direct for %s" \
                % (datetime.datetime.now(), dev)
        raise
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
    except OSError as e:
        print "%s: encounter error in writeat_direct for %s" \
                % (datetime.datetime.now(), dev)
        raise
    finally:
        m.close()
        os.close(f)
    return ret

def write_data(thread, index, pattern):
    writeat_direct("/dev/longhorn/vol%d" % (thread), index * PAGE_SIZE, str(chr(pattern))*PAGE_SIZE)

def check_data(thread, index, pattern):
    data = readat_direct("/dev/longhorn/vol%d" % (thread), index * PAGE_SIZE, PAGE_SIZE)
    assert ord(data[0]) == pattern

def create_snapshot(controller):
  return subprocess.Popen(("docker exec " + controller + " longhorn snapshot create").split(), stdout=subprocess.PIPE).communicate()[0].rstrip()

def revert_snapshot(snap, controller):
  proc = subprocess.Popen(("docker exec " + controller + " longhorn snapshot revert " + snap).split(), stdout=subprocess.PIPE)
  proc.communicate()[0]
  return proc.returncode

def wait_for_dev_ready(thread, iteration, controller):
  dev = "/dev/longhorn/vol%d" % (thread)
  init_time = time.time()
  while time.time() - init_time < 60:
    if os.path.exists(dev):
      mode = os.stat(dev).st_mode
      if stat.S_ISBLK(mode):
        print "%s: thread = %d iteration = %d Device ready after %.3f seconds" \
                % (datetime.datetime.now(), thread, iteration, time.time() - init_time)
        return
    time.sleep(0.05)
  print "%s: thread = %d iteration = %d FAIL TO WAIT FOR DEVICE READY, docker logs:" \
          % (datetime.datetime.now(), thread, iteration)
  subprocess.call("docker logs " + controller, shell=True)
  return

count = 0

def rebuild_replica(thread, controller, replica_num, replica):
  global count
  replica_host = "172.18.%d.%d" % (replica_num, thread)
  replica_host_port = replica_host + ":9502"
  subprocess.call("docker kill %s" % (replica), shell=True)
  count = count + 1
  newreplica = subprocess.Popen(("docker run -d --name r%d-%d-%d" % (replica_num, thread, count) + \
        " --net longhorn-net --ip %s --expose 9502-9504 -v /volume" % (replica_host) + \
        " rancher/longhorn launch replica --listen %s --size %d /volume" \
        % (replica_host_port, DATA_LEN)).split(), stdout=subprocess.PIPE).communicate()[0].rstrip()
  print "%s: thread = %d new replica%d = %s" % (datetime.datetime.now(), thread, replica_num, newreplica)

  subprocess.call(("docker exec " + controller + " longhorn rm tcp://" + replica_host_port).split())
  subprocess.call(("docker exec " + controller + " longhorn add tcp://" + replica_host_port).split())
  subprocess.call("docker rm -fv %s" % (replica), shell=True)
  return newreplica


def get_snapshot_list(controller):
    snapshots = subprocess.check_output("docker exec " + controller +
                " longhorn snapshots | tail -n +3", shell=True)
    return snapshots.split()

def rebuild_replicas(thread, controller, replica1, replica2):
  while True:
    print "%s: thread = %d rebuild replica test start" \
              % (datetime.datetime.now(), thread)
    if random.random() < 0.5:
      replica1 = rebuild_replica(thread, controller, 1, replica1)
    else:
      replica2 = rebuild_replica(thread, controller, 2, replica2)
    for snapshot in get_snapshot_list(controller):
        snapshots = subprocess.check_output("docker exec " + controller +
                " longhorn snapshots rm " + snapshot, shell=True)
    print "%s: thread = %d rebuild replica test ends and snapshot cleaned up" \
              % (datetime.datetime.now(), thread)

def read_write(thread, iterations):
  replica1 = subprocess.Popen(("docker run -d --name r1-%d" % (thread) + \
        " --net longhorn-net --ip 172.18.1.%d --expose 9502-9504 -v /volume" % (thread) + \
        " rancher/longhorn launch replica --listen 172.18.1.%d:9502 --size %d /volume" \
        % (thread, DATA_LEN)).split(), stdout=subprocess.PIPE).communicate()[0].rstrip()
  print "%s: thread = %d replica1 = %s" % (datetime.datetime.now(), thread, replica1)
  replica2 = subprocess.Popen(("docker run -d --name r2-%d" % (thread) + \
        " --net longhorn-net --ip 172.18.2.%d --expose 9502-9504 -v /volume" % (thread) + \
        " rancher/longhorn launch replica --listen 172.18.2.%d:9502 --size %d /volume" \
        % (thread, DATA_LEN)).split(), stdout=subprocess.PIPE).communicate()[0].rstrip()
  print "%s: thread = %d replica2 = %s" % (datetime.datetime.now(), thread, replica2)
  controller = subprocess.Popen(("docker run -d --name c-%d" % (thread)+ \
        " --net longhorn-net --privileged -v /dev:/host/dev" + \
        " -v /proc:/host/proc rancher/longhorn launch controller --frontend tgt" + \
        " --replica tcp://172.18.1.%d:9502 --replica tcp://172.18.2.%d:9502 vol%d" \
        % (thread, thread, thread)).split(), stdout=subprocess.PIPE).communicate()[0].rstrip()
  print "%s: controller = %s" % (datetime.datetime.now(), controller)
  wait_for_dev_ready(thread, -1, controller)

  rebuild_proc = Process(target = rebuild_replicas, args = (thread, controller, replica1, replica2))
  rebuild_proc.start()

  try:
    for iteration in xrange(iterations):
      print "%s: thread = %d iteration = %d started" \
                % (datetime.datetime.now(), thread, iteration)
      pattern1 = int(255 * random.random())
      index = int(NUM_PAGES * random.random())
      index2 = int(NUM_PAGES * random.random())
      write_data(thread, index, pattern1)
      write_data(thread, index2, pattern1)
      check_data(thread, index, pattern1)
      check_data(thread, index2, pattern1)
      snapshot_count = len(get_snapshot_list(controller))
      print "%s: thread = %d iteration = %d current snapshot counts %d" \
                  % (datetime.datetime.now(), thread, iteration, snapshot_count)
      # We cannot take more snapshots, just wait util they got removed
      if snapshot_count > 100:
          print "%s: thread = %d iteration = %d skip snapshot, waiting for removal" \
                  % (datetime.datetime.now(), thread, iteration)
          continue
      snap = create_snapshot(controller)
      if not snap:
        continue
      pattern2 = int(255 * random.random())
      write_data(thread, index, pattern2)
      check_data(thread, index, pattern2)
      if index2 != index:
        check_data(thread, index2, pattern1)
      print "%s: thread = %d iteration = %d snapshot created %s and verified" \
                % (datetime.datetime.now(), thread, iteration, snap)
      # Skip snapshot tests for now as we cannot revert snapshots for volumes being rebuilt.
      continue
      if revert_snapshot(snap, controller) != 0:
          continue
      wait_for_dev_ready(thread, iteration, controller)
      check_data(thread, index, pattern1)
      if index2 != index:
        check_data(thread, index2, pattern1)
  finally:
    rebuild_proc.terminate()

workers = []

nthreads = 10

for thread in xrange(nthreads):
  p = Process(target = read_write, args = (thread + 1, 100000))
  workers.append(p)
  p.start()


for p in workers:
  p.join()
