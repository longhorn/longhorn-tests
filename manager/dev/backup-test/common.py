import time
import longhorn

# constants
RETRY_COUNTS = 60
RETRY_INTERVAL = 1
VOLUME_FIELD_STATE = "state"
VOLUME_STATE_ATTACHED = "attached"
VOLUME_STATE_DETACHED = "detached"
VOLUME_FIELD_ROBUSTNESS = "robustness"
VOLUME_ROBUSTNESS_HEALTHY = "healthy"


def wait_for_volume_status(client, name, key, value):
    wait_for_volume_creation(client, name)
    volume = client.by_id_volume(name)
    for i in range(RETRY_COUNTS):
        volume = client.by_id_volume(name)
        if volume[key] == value:
            return volume
        time.sleep(RETRY_INTERVAL)
    assert volume[key] == value
    return volume


def wait_for_volume_creation(client, name):
    for i in range(RETRY_COUNTS):
        volumes = client.list_volume()
        for volume in volumes:
            if volume.name == name:
                return
        time.sleep(RETRY_INTERVAL)
    assert False


def wait_for_volume_attached(client, name):
    return wait_for_volume_status(client, name,
                                  VOLUME_FIELD_STATE,
                                  VOLUME_STATE_ATTACHED)


def wait_for_volume_detached(client, name):
    return wait_for_volume_status(client, name,
                                  VOLUME_FIELD_STATE,
                                  VOLUME_STATE_DETACHED)


def wait_for_volume_healthy(client, name):
    wait_for_volume_status(client, name,
                           VOLUME_FIELD_STATE,
                           VOLUME_STATE_ATTACHED)
    wait_for_volume_status(client, name,
                           VOLUME_FIELD_ROBUSTNESS,
                           VOLUME_ROBUSTNESS_HEALTHY)
    return wait_for_volume_endpoint(client, name)


def wait_for_volume_endpoint(client, name):
    for i in range(RETRY_COUNTS):
        v = client.by_id_volume(name)
        engine = get_volume_engine(v)
        if engine.endpoint != "":
            return v
        time.sleep(RETRY_INTERVAL)
    assert False


def get_volume_engine(v):
    engines = v.controllers
    assert len(engines) != 0
    return engines[0]
