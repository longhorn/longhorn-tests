import logging
from utility.utility import init_k8s_api_client
import utils.common_utils

class common_keywords:

    def set_test_environment(self):
        init_k8s_api_client()

    def generate_support_bundle(self, case_name):
        logging.info(f"generating support bundle for {case_name}")
        common_utils.generate_support_bundle(case_name)
