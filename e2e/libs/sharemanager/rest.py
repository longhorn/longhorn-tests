from sharemanager.base import Base

from utility.utility import get_longhorn_client


class Rest(Base):

    def __init__(self):
        self.longhorn_client = get_longhorn_client()

    def list(self):
        return self.longhorn_client.list_share_manager()
