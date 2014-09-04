class GameEntry(object):
    def __init__(self, name, icon, path, tryexec=None):
        self.name = name
        self.icon = icon
        self.path = path
        self.tryexec = tryexec or path

    def __str__(self):
        return self.name

    def __repr__(self):
        return "%s (%s)" % (self.name, self.path)
