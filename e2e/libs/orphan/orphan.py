import os
import time

from node_exec import NodeExec
from volume.rest import Rest as Volume
from utility.utility import logging
from utility.utility import generate_random_id
from utility.utility import get_retry_count_and_interval
from utility.utility import get_longhorn_client

class Orphan:

    def __init__(self):
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def wait_for_orphan_count(self, count):
        longhorn_client = get_longhorn_client()
        for i in range(self.retry_count):
            orphans = longhorn_client.list_orphan()
            logging(f"Waiting for orphan count to be {count}, currently it's {len(orphans)} ... ({i})")
            if len(orphans) == int(count):
                return
            time.sleep(self.retry_interval)
        assert False, f"Failed to wait orphan count to be {count}"

    def delete_orphan(self, orphan):
        longhorn_client = get_longhorn_client()
        try:
            longhorn_client.delete(orphan)
        except Exception as e:
            logging(f"Deleting orphan {orphan.name} error: {e}")

        for i in range(self.retry_count):
            logging(f"Waiting for orphan {orphan.name} to be deleted ... ({i})")
            try:
                orphans = longhorn_client.list_orphan()
                if orphan.name in [o.name for o in orphans]:
                    time.sleep(self.retry_interval)
                    continue
                return
            except Exception as e:
                logging(f"Waiting for orphan {orphan.name} to be deleted error: {e}")

        assert False, f"Failed to delete orphan {orphan.name}"

    def delete_orphans(self):
        orphans = get_longhorn_client().list_orphan()
        logging(f"Deleting {len(orphans)} orphans")
        for orphan in orphans:
            self.delete_orphan(orphan)
