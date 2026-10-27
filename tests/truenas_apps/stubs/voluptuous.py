class Schema:
    def __init__(self, s):
        self.schema = s


class Required(str):
    def __new__(cls, k, default=None):
        return str.__new__(cls, k)


def Match(p):
    return str


def All(*a):
    return str


Strip = object()
