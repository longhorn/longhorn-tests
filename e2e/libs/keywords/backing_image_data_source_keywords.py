from backing_image_data_source import BackingImageDataSource


class backing_image_data_source_keywords:

    def __init__(self):
        self.backing_image_data_source = BackingImageDataSource()

    def wait_for_backing_image_data_source_created(self, backing_image_data_source_name):
        self.backing_image_data_source.wait_for_created(backing_image_data_source_name)

    def get_backing_image_data_source_node_id(self, backing_image_data_source_name):
        return self.backing_image_data_source.get_node_id(backing_image_data_source_name)

    def wait_for_backing_image_data_source_state(self, backing_image_data_source_name, state):
        self.backing_image_data_source.wait_for_state(backing_image_data_source_name, state)

    def backing_image_data_source_should_not_be_in_state(self, backing_image_data_source_name, state):
        self.backing_image_data_source.should_not_be_in_state(backing_image_data_source_name, state)
