def check_replica_locality(replica_locality):
    assert replica_locality in ["replica node", "volume node"], f"Unknown replica locality: {replica_locality}: "
