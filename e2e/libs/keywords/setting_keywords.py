import json
from setting import Setting
from node import Node
from utility.utility import logging


class setting_keywords:

    def __init__(self):
        self.setting = Setting()
        self.node = Node()

    def update_setting(self, key, value, retry=True):
        self.setting.update_setting(key, value, retry)

    def get_setting(self, key):
        return self.setting.get_setting(key)

    def reset_settings(self, data_engine="v1"):
        self.setting.reset_settings(data_engine)

    def get_expected_rps_cpus_regex(self, node_name, isolation_enabled=True):
        if isinstance(isolation_enabled, str):
            isolation_enabled = isolation_enabled.lower() == 'true'

        cpu_cores = int(self.node.get_node_cpu_cores(node_name))
        all_cpus_mask = (1 << cpu_cores) - 1

        if not isolation_enabled:
            expected_mask = all_cpus_mask
        else:
            raw_setting = self.get_setting("data-engine-cpu-mask")
            mask_str = "0x1"
            try:
                setting_dict = json.loads(raw_setting)
                if isinstance(setting_dict, dict):
                    mask_str = setting_dict.get("v2", "0x1")
                elif isinstance(setting_dict, (int, str)):
                    mask_str = str(setting_dict)
            except (ValueError, TypeError):
                mask_str = raw_setting if raw_setting else "0x1"

            spdk_mask = int(mask_str, 16) if str(mask_str).startswith("0x") else int(mask_str)
            expected_mask = all_cpus_mask & ~spdk_mask

        expected_hex = f"{expected_mask:x}"
        logging(f"Node {node_name} ({cpu_cores} CPUs): isolation={isolation_enabled}, expected_rps={expected_hex}")
        return f"(?i)0*{expected_hex}\\s*$"
