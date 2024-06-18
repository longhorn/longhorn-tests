from service.service import is_services_headless

from sharemanager import ShareManager
from sharemanager.constant import LABEL_SHAREMANAGER


class sharemanager_keywords:

    def __init__(self):
        self.sharemanager = ShareManager()

    def is_sharemanagers_using_headless_service(self):
        not_headless_services = []
        sharemanagers = self.sharemanager.list()
        for sharemanager in sharemanagers['items']:
            sharemanager_name = sharemanager['metadata']['name']
            label_selector = f"{LABEL_SHAREMANAGER}={sharemanager_name}"
            if not is_services_headless(label_selector=label_selector):
                not_headless_services.append(sharemanager_name)

        if len(not_headless_services) == 0:
            return True

        return False
