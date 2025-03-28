from engine_image import EngineImage


class engine_image_keywords:

    def __init__(self):
        self.engine_image = EngineImage()

    def deploy_compatible_engine_image(self):
        return self.engine_image.deploy_compatible_engine_image()

    def wait_for_engine_image_deployed(self, image_name):
        return self.engine_image.wait_for_engine_image_deployed(image_name)

    def cleanup_engine_images(self):
        return self.engine_image.cleanup_engine_images()
