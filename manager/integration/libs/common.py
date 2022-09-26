
def create_volume(size, replica_count):
    print('create_volume')
    return 'test_volume_name'


def write_volume_random_data(size_in_mb, volume_name):
    print('write_volume_random_data')
    return 'checksum'


def check_data(volume_name, checksum):
    print('get_volume_data_checksum')


def delete_replica(volume_name, replica_index):
    print('delete_replica_to_trigger_rebuilding')


def wait_for_replica_rebuilding_start(volume_name, replica_index):
    print('wait_for_replica_rebuilding_start')


def wait_for_replica_rebuilding_complete(volume_name, replica_index):
    print('wait_for_replica_rebuilding_complete')
