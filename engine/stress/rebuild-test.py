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
    if ord(data[0]) != pattern:
        print "Expected %s but get %s at index %d for vol%d" % (pattern,
                data[0], index, thread)
    assert ord(data[0]) == pattern

def create_snapshot(controller):
  return subprocess.check_output(("docker exec " + controller + " longhorn snapshot create").split()).rstrip()

def revert_snapshot(snap, controller):
  subprocess.check_call(("docker exec " + controller + " longhorn snapshot revert " + snap).split())

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

def get_new_ip(thread, ip1, ip2):
  while True:
      # avoid controller ip
      subnet = int(252 * random.random()) + 2
      ip = "172.18.%s.%s" % (subnet, thread)
      if ip != ip1 and ip != ip2:
          break
  return ip

count = 0


def rebuild_replica(thread, controller, replica_num, replica, rebuild_ip, remain_ip):
  global count
  replica_host = get_new_ip(thread, rebuild_ip, remain_ip)
  replica_host_port = replica_host + ":9502"
  rebuild_host_port = rebuild_ip + ":9502"
  subprocess.call("docker kill %s" % (replica), shell=True)
  count = count + 1
  newreplica = subprocess.check_output(("docker run -d --name r%d-%d-%d" % (replica_num, thread, count) + \
        " --net longhorn-net --ip %s --expose 9502-9504 -v /volume" % (replica_host) + \
        " rancher/longhorn launch replica --listen %s --size %d /volume" \
        % (replica_host_port, DATA_LEN)).split()).rstrip()

  print "%s: thread = %d remove old replica%d = %s ip = %s" % (datetime.datetime.now(),
          thread, replica_num, replica, rebuild_ip)
  subprocess.check_call(("docker exec " + controller + " longhorn rm tcp://" + rebuild_host_port).split())

  print "%s: thread = %d create new replica%d = %s ip = %s" % (datetime.datetime.now(),
          thread, replica_num, newreplica, replica_host)
  subprocess.check_call(("docker exec " + controller + " longhorn add tcp://" + replica_host_port).split())
  subprocess.check_call("docker rm -fv %s" % (replica), shell=True)
  return newreplica, replica_host


def get_snapshot_list(controller):
    snapshots = subprocess.check_output("docker exec " + controller +
                " longhorn snapshots | tail -n +3", shell=True)
    return snapshots.split()

def rebuild_replicas(thread, controller, replica1, replica1_ip, replica2, replica2_ip):
  while True:
    print "%s: thread = %d rebuild replica test start" \
              % (datetime.datetime.now(), thread)
    if random.random() < 0.5:
      replica1, replica1_ip = rebuild_replica(thread, controller, 1, replica1,
              replica1_ip, replica2_ip)
    else:
      replica2, replica2_ip = rebuild_replica(thread, controller, 2, replica2,
              replica2_ip, replica1_ip)
    for snapshot in get_snapshot_list(controller):
        snapshots = subprocess.check_output("docker exec " + controller +
                " longhorn snapshots rm " + snapshot, shell=True)
    print "%s: thread = %d rebuild replica test ends and snapshot cleaned up" \
              % (datetime.datetime.now(), thread)

def read_write(thread, iterations):
  replica1_ip = "172.18.2.%d" % (thread)
  replica1 = subprocess.check_output(("docker run -d --name r1-%d" % (thread) + \
        " --net longhorn-net --ip %s --expose 9502-9504 -v /volume" % (replica1_ip) + \
        " rancher/longhorn launch replica --listen %s:9502 --size %d /volume" \
        % (replica1_ip, DATA_LEN)).split()).rstrip()
  print "%s: thread = %d name = r1-%d replica1 = %s ip = %s" \
          % (datetime.datetime.now(), thread, thread, replica1, replica1_ip)
  replica2_ip = "172.18.3.%d" % (thread)
  replica2 = subprocess.check_output(("docker run -d --name r2-%d" % (thread) + \
        " --net longhorn-net --ip %s --expose 9502-9504 -v /volume" % (replica2_ip) + \
	" rancher/longhorn launch replica --listen %s:9502 --size %d /volume" \
        % (replica2_ip, DATA_LEN)).split()).rstrip()
  print "%s: thread = %d name = r2-%d replica2 = %s ip = %s" \
          % (datetime.datetime.now(), thread, thread, replica2, replica2_ip)
  controller_ip = "172.18.1.%d" % (thread)
  controller = subprocess.check_output(("docker run -d --name c-%d" % (thread)+ \
        " --net longhorn-net --ip %s --privileged -v /dev:/host/dev" % (controller_ip) + \
        " -v /proc:/host/proc rancher/longhorn launch controller --frontend tgt" + \
        " --replica tcp://%s:9502 --replica tcp://%s:9502 vol%d" \
        % (replica1_ip, replica2_ip, thread)).split()).rstrip()
  print "%s: thread = %d name = c-%d controller = %s ip = %s" \
          % (datetime.datetime.now(), thread, thread, controller, controller_ip)
  wait_for_dev_ready(thread, -1, controller)

  rebuild_proc = Process(target = rebuild_replicas, args = (thread, controller,\
          replica1, replica1_ip, replica2, replica2_ip))
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

for thread in range(nthreads):
  p = Process(target = read_write, args = (thread + 1, 100000))
  workers.append(p)
  p.start()


for p in workers:
  p.join()
