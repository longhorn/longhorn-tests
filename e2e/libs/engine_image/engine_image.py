import time

from utility.utility import get_longhorn_client
from utility.utility import get_retry_count_and_interval
from utility.utility import logging


class EngineImage():

    UPGRADE_TEST_IMAGE_PREFIX = "longhornio/longhorn-test:upgrade-test"

    def __init__(self):
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def get_default_engine_image(self):
        images = get_longhorn_client().list_engine_image()
        for img in images:
            if img.default:
                return img
        assert False, f"Failed to get default engine image: {images}"

    def get_default_engine_image_versions(self):
        default_img = self.get_default_engine_image()
        cli_v = default_img.cliAPIVersion
        cli_minv = default_img.cliAPIMinVersion
        ctl_v = default_img.controllerAPIVersion
        ctl_minv = default_img.controllerAPIMinVersion
        data_v = default_img.dataFormatVersion
        data_minv = default_img.dataFormatMinVersion
        return cli_v, cli_minv, ctl_v, ctl_minv, data_v, data_minv

    def deploy_compatible_engine_image(self):
        cli_v, cli_minv, ctl_v, ctl_minv, data_v, data_minv = self.get_default_engine_image_versions()
        compatible_engine_image_name = \
            f"{self.UPGRADE_TEST_IMAGE_PREFIX}.{cli_v}-{cli_minv}.{ctl_v}-{ctl_minv}.{data_v}-{data_minv}"
        image = self.create_engine_image(compatible_engine_image_name)
        return image.image

    def create_engine_image(self, image_name):
        image = get_longhorn_client().create_engine_image(image=image_name)
        image = self.wait_for_engine_image_deployed(image.name)
        assert image.refCount == 0, f"Expected new engine image {image_name} refCount == 0, but it's {image.refCount}"
        assert image.noRefSince != "", f"Expected new engine image {image_name} noRefSince not empty, but it's {image.noRefSince}"
        return image

    def wait_for_engine_image_deployed(self, image_name):
        self.wait_for_engine_image_created(image_name)
        for i in range(self.retry_count):
            logging(f"Waiting for engine image {image_name} to be deployed ... ({i})")
            try:
                image = get_longhorn_client().by_id_engine_image(image_name)
                if image.state == "deployed":
                    break
            except Exception as e:
                logging(f"Failed to deploy engine image {image_name}: {e}")
            time.sleep(self.retry_interval)
        assert image.state == "deployed", f"Failed to deploy engine image {image_name}: {image}"
        return image

    def wait_for_engine_image_ref_count(self, image_name, count):
        self.wait_for_engine_image_created(image_name)
        for i in range(self.retry_count):
            image = get_longhorn_client().by_id_engine_image(image_name)
            if image.refCount == count:
                break
            time.sleep(self.retry_interval)
        assert image.refCount == count, f"Failed to wait engine image {image_name} reference count {count}: {image}"
        if count == 0:
            assert image.noRefSince != "", f"Expected engine image {image_name} noRefSince non-empty: {image}"
        return image

    def wait_for_engine_image_created(self, image_name):
        for i in range(self.retry_count):
            images = get_longhorn_client().list_engine_image()
            found = False
            for img in images:
                if img.name == image_name:
                    found = True
                    break
            if found:
                break
            time.sleep(self.retry_interval)
        assert found, f"Failed to create engine image {image_name}: {images}"

    def cleanup_engine_images(self):
        logging(f"Cleaning up engine images")
        images = get_longhorn_client().list_engine_image().data
        for image in images:
            if not image.default:
                logging(f"Cleaning up engine image {image.name}")
                self.wait_for_engine_image_ref_count(image.name, 0)
                get_longhorn_client().delete(image)
                self.wait_for_engine_image_deleted(image.name)

    def wait_for_engine_image_deleted(self, image_name):

        deleted = False

        for i in range(self.retry_count):

            time.sleep(self.retry_interval)
            deleted = True

            images = get_longhorn_client().list_engine_image().data
            for image in images:
                if image.name == image_name:
                    deleted = False
                    break
            if deleted:
                break

        assert deleted, f"Failed to delete engine image {image_name}: {images}"
