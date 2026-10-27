from enum import IntFlag


class UpdateEntityFeature(IntFlag):
    INSTALL = 1


class UpdateEntity:
    entity_picture = None
    release_url = None
    extra_state_attributes = None
