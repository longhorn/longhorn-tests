from secret import Secret

from kubernetes.client.rest import ApiException


class secret_keywords:

    def __init__(self):
        self.secret = Secret()

    def create_secret(self, name=None):
        self.secret.create(name=name)

    def assert_secret_does_not_exist(self, name):
        try:
            data = self.secret.get_data(name)
        except ApiException as e:
            if e.status == 404:
                return
            raise
        assert False, f"secret {name} exists and carries {sorted(data)}"

    def cleanup_secrets(self):
        self.secret.cleanup()
