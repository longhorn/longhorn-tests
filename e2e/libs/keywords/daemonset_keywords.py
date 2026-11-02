from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE
from utility.utility import logging

from workload.daemonset import create_daemonset
from workload.daemonset import delete_daemonset
from workload.daemonset import list_daemonsets


class daemonset_keywords:

    def cleanup_daemonsets(self):
        daemonsets = list_daemonsets(
            label_selector=f"{LABEL_TEST}={LABEL_TEST_VALUE}"
        )

        logging(f'Cleaning up {len(daemonsets.items)} daemonsets')
        for daemonset in daemonsets.items:
            self.delete_daemonset(daemonset.metadata.name)

    def create_daemonset(self, name, claim_name, args=None, wait=True):
        logging(f'Creating daemonset {name}')
        create_daemonset(name, claim_name, args=args, wait=wait)

    def delete_daemonset(self, name):
        logging(f'Deleting daemonset {name}')
        delete_daemonset(name)

