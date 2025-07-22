from backup_backing_image import BackupBackingImage

from utility.utility import logging


class backup_backing_image_keywords:

    def __init__(self):
        self.backupbackingimage = BackupBackingImage()

    def create_backup_backing_image(self, backing_image_name, backup_backing_image_name):
        self.backupbackingimage.create(backing_image_name, backup_backing_image_name)

    def wait_for_backup_backing_image_ready(self, backup_backing_image_name):
        self.backupbackingimage.wait_for_backup_backing_image_ready(backup_backing_image_name)

    def wait_for_backup_backing_image_for_backing_image_ready(self, backing_image_name):
        self.backupbackingimage.wait_for_backup_backing_image_for_backing_image_ready(backing_image_name)

    def cleanup_backup_backing_images(self):
        self.backupbackingimage.cleanup_backup_backing_images()
