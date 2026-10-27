from enum import StrEnum


class TextSelectorType(StrEnum):
    PASSWORD = "password"


class TextSelectorConfig:
    def __init__(self, type=None):
        self.type = type


class TextSelector:
    def __init__(self, config=None):
        pass
