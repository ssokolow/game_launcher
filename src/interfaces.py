from yapsy.IPlugin import IPlugin

# TODO: Look into implementing dependences using
#       https://pypi.python.org/pypi/toposort

class IGameProvider(IPlugin):
    """Base class for game provider plugins"""
    plugin_type = "Game Provider"
    backend_name = None

    # TODO: Some kind of priority/precedence system
    # TODO: Inter-plugin dependencies
    # TODO: An interface for specifying external dependencies like ScummVM
    #       to block plugin activation and display an explanatory message.

    def __str__(self):
        return "{} ({})".format(self.backend_name, self.plugin_type)

    def get_games(self):
        raise NotImplementedError("Override this to retrieve the list of games"
                                  "offered by this provider.")

    def get_saves(self, game_id):
        raise NotImplementedError("Override to retrieve saves for a given game"
                                  " if launching straight into a save is "
                                  "supported.")

PLUGIN_TYPES = [IGameProvider]
