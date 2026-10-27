def callback(f):
    return f


class _CE:
    def __init__(self):
        self.reloads = []

    def async_schedule_reload(self, eid):
        self.reloads.append(eid)

    async def async_forward_entry_setups(self, entry, platforms):
        pass

    async def async_unload_platforms(self, entry, platforms):
        return True


class HomeAssistant:
    def __init__(self):
        self.config_entries = _CE()
        self.session = None
        self.notifications = {}
