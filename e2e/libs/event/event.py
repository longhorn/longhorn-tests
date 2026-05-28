import json
from datetime import datetime, timedelta, timezone

import utility.constant as constant
from utility.utility import logging
from utility.utility import subprocess_exec_cmd


def get_events(namespace=constant.LONGHORN_NAMESPACE, field_selector=None, start_time=None):
    """
    Get Kubernetes events from the specified namespace.

    Args:
        namespace: Kubernetes namespace to query
        field_selector: Filter events by field selector (e.g., "involvedObject.name=volume-1,involvedObject.kind=Volume")
        start_time: Only return events after this datetime (must be timezone-aware or will be treated as UTC)

    Returns:
        List of event items, optionally filtered by field_selector and start_time
    """
    cmd = f"kubectl get event -n {namespace} --sort-by='.lastTimestamp' -ojson"

    if field_selector:
        cmd += f" --field-selector='{field_selector}'"

    try:
        events = json.loads(subprocess_exec_cmd(cmd, verbose=False))
        items = events.get('items', [])

        if start_time:
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)

            filtered_items = []
            for event in items:
                # Parse lastTimestamp from the event
                last_timestamp_str = event.get('lastTimestamp')
                if last_timestamp_str:
                    last_timestamp = datetime.fromisoformat(last_timestamp_str.replace('Z', '+00:00'))
                    if last_timestamp >= start_time:
                        filtered_items.append(event)

            return filtered_items

        return items
    except Exception as e:
        logging(f"Failed to get events in namespace {namespace}: {e}")
        return []

def cleanup_events(namespace=constant.LONGHORN_NAMESPACE):
    logging(f"Cleaned up events in namespace {namespace}")
    cmd = f"kubectl delete event -n {namespace} --all"
    subprocess_exec_cmd(cmd, verbose=False)
