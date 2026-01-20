from support_bundle.support_bundle import generate_support_bundle
from support_bundle.support_bundle import check_bundle_contains_host_logs


class support_bundle_keywords:

    def generate_support_bundle(self, download=False):
        generate_support_bundle(download)

    def check_bundle_contains_host_logs(self, host_log_files, node_name, bundle_zip_path="./lh-support-bundle.zip"):
        check_bundle_contains_host_logs(host_log_files, node_name, bundle_zip_path)
