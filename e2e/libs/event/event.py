import json
from datetime import datetime, timedelta, timezone

import utility.constant as constant
from utility.utility import logging
from utility.utility import subprocess_exec_cmd


def get_events(namespace=constant.LONGHORN_NAMESPACE):
    cmd = f"kubectl get event -n {namespace} --sort-by='.lastTimestamp' -ojson"
    try:
        events = json.loads(subprocess_exec_cmd(cmd, verbose=False))
        return events.get('items', [])
    except Exception as e:
        logging(f"Failed to get events in namespace {namespace}: {e}")
        return []

def cleanup_events(namespace=constant.LONGHORN_NAMESPACE):
    logging(f"Cleaned up events in namespace {namespace}")
    cmd = f"kubectl delete event -n {namespace} --all"
    subprocess_exec_cmd(cmd, verbose=False)
