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
#subprocess.call("docker rm -fv `docker ps -a | grep rancher/longhorn | awk '{print $1}'`", shell=True)
subprocess.call("docker rm -fv `docker ps -qa`", shell=True)
subprocess.call("docker network rm longhorn-net", shell=True)
subprocess.call("docker network create --subnet=172.18.0.0/16 longhorn-net", shell=True)

NUM_PAGES = 16

PAGE_SIZE = 4096

DATA_LEN = NUM_PAGES * PAGE_SIZE

MAX_RETRY = 5

WAIT_TIMEOUT = 300

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
        print "%s: encounter error in readat_direct for %s" \
                % (datetime.datetime.now(), dev)
        raise
    finally:
        m.close()
        os.close(f)
    return ret

def write_data(i, pattern):
  for page in xrange(0, NUM_PAGES):
    writeat_direct("/dev/longhorn/vol" + str(i), page * PAGE_SIZE, str(chr(pattern))*PAGE_SIZE)

def check_data(i, pattern):
  for page in xrange(0, NUM_PAGES):
    data = readat_direct("/dev/longhorn/vol" + str(i), page * PAGE_SIZE, PAGE_SIZE)
    assert ord(data[0]) == pattern

def create_snapshot(controller):
  return subprocess.check_output(("docker exec " + controller + " launch snapshot create").split()).rstrip()

def revert_snapshot(snap, controller):
  subprocess.check_call("docker exec " + controller + " launch snapshot revert " + snap, shell = True)

def wait_for_dev_ready(i, iteration, controller):
  dev = "/dev/longhorn/vol" + str(i)
  init_time = time.time()
  while time.time() - init_time < WAIT_TIMEOUT:
    if os.path.exists(dev):
      mode = os.stat(dev).st_mode
      if stat.S_ISBLK(mode):
        print "%s: iteration = %d thread = %d : Device ready after %.3f seconds" \
                % (datetime.datetime.now(), iteration, i, time.time() - init_time)
        return
    time.sleep(0.05)
  print "%s: iteration = %d thread = %d : FAIL TO WAIT FOR DEVICE READY, docker logs:" \
          % (datetime.datetime.now(), iteration, i)
  subprocess.call("docker logs " + controller, shell=True)
  return

def wait_for_dev_deleted(i, iteration, controller):
  dev = "/dev/longhorn/vol" + str(i)
  init_time = time.time()
  while time.time() - init_time < WAIT_TIMEOUT:
    if not os.path.exists(dev):
        print "%s: iteration = %d thread = %d : Device deleted after %.3f seconds" \
                % (datetime.datetime.now(), iteration, i, time.time() - init_time)
        return
    time.sleep(0.05)
  print "%s: iteration = %d thread = %d : FAIL TO WAIT FOR DEVICE DELETED, docker logs:" \
          % (datetime.datetime.now(), iteration, i)
  subprocess.call("docker logs " + controller, shell=True)
  return


def run_test(thread, iterations):
  for iteration in xrange(iterations):
    replica1_ip = "172.18.%d.%d" % (iteration % 80 + 1, thread)
    replica1 = subprocess.check_output(("docker run -d --name r1-%d-%d" % (iteration, thread) + \
        " --net longhorn-net --ip %s --expose 9502-9504 -v /volume" % (replica1_ip) + \
        " rancher/longhorn launch replica --listen %s:9502 --size %d /volume" \
        % (replica1_ip, DATA_LEN)).split()).rstrip()
    print "%s: iteration = %d thread = %d name = r1-%d-%d replica1 = %s ip = %s" \
            % (datetime.datetime.now(), iteration, thread, iteration, thread,
                    replica1, replica1_ip)
    replica2_ip = "172.18.%d.%d" % (iteration % 80 + 81, thread)
    replica2 = subprocess.check_output(("docker run -d --name r2-%d-%d" % (iteration, thread) + \
        " --net longhorn-net --ip %s --expose 9502-9504 -v /volume" % (replica2_ip) + \
        " rancher/longhorn launch replica --listen %s:9502 --size %d /volume" \
        % (replica2_ip, DATA_LEN)).split()).rstrip()
    print "%s: iteration = %d thread = %d name = r2-%d-%d replica2 = %s ip = %s" \
            % (datetime.datetime.now(), iteration, thread, iteration, thread,
                    replica2, replica2_ip)
    controller_ip = "172.18.%d.%d" % (iteration % 80 + 161, thread)
    controller_name = "c-%d-%d" % (iteration, thread)
    started = False
    count = 0
    print "About to create controller for " + controller_name
    while not started and count < MAX_RETRY:
        try:
            controller = subprocess.check_output(("docker run -d --name %s" % (controller_name) + \
                    " --net longhorn-net --ip %s --privileged -v /dev:/host/dev" % (controller_ip) + \
                    " -v /proc:/host/proc rancher/longhorn launch controller --frontend tgt" + \
                    " --replica tcp://%s:9502 --replica tcp://%s:9502 vol%d" \
                    % (replica1_ip, replica2_ip, thread)).split()).rstrip()
            print "controller %s created as %s" % (controller_name, controller)
            started = True
        except subprocess.CalledProcessError as ex:
            status = subprocess.check_output(
                "docker ps -a -f NAME=%s --format {{.Status}}" \
                % (controller_name), shell=True)
            if status != "" and status.strip() != "Created":
                raise ex
            # Now we know it's the Docker race bug
            print "Docker's bug result in failed to start controller, retrying: " + str(ex)
            subprocess.call("docker rm -fv " + controller_name, shell=True)
            time.sleep(1)
            count += 1

    assert started

    wait_for_dev_ready(thread, iteration, controller)
    print "%s: iteration = %d thread = %d name = c-%d-%d controller = %s ip = %s" \
            % (datetime.datetime.now(), iteration, thread, iteration, thread,
                    controller, controller_ip)
    pattern1 = int(255 * random.random())
    write_data(thread, pattern1)
    check_data(thread, pattern1)
    snap = create_snapshot(controller)
    assert snap != ""
    pattern2 = int(255 * random.random())
    write_data(thread, pattern2)
    check_data(thread, pattern2)
    if random.random() < 0.1:
      print "%s: iteration = %d thread = %d sleep 30 seconds" \
            % (datetime.datetime.now(), iteration, thread)
      time.sleep(30)
    revert_snapshot(snap, controller)
    wait_for_dev_ready(thread, iteration, controller)
    check_data(thread, pattern1)
    subprocess.call("docker stop %s" % (controller), shell=True)
    wait_for_dev_deleted(thread, iteration, controller)
    subprocess.call("docker stop %s %s" % (replica1, replica2), shell=True)
    subprocess.call("docker rm -fv %s %s %s" % (controller, replica1, replica2), shell=True)

workers = []

for thread in range(20):
  p = Process(target = run_test, args = (thread + 1, 1000))
  workers.append(p)
  p.start()


for p in workers:
  p.join()
