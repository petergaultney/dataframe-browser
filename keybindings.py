# supports multiple keybindings per command
_commands = { # these commands are specifically for use in the browser
    'merge': ['m'],
    'hide column': ['H'],
    'search down': ['ctrl s'],
    'search up': ['ctrl r'],
    'sort ascending': ['s'],
    'sort descending': ['r'],
    'browse right': ['right', 'l'],
    'browse left': ['left', 'h'],
    'browse up': ['up', 'k'],
    'browse down': ['down', 'j'],
    'undo': ['u', 'ctrl /'],
    'quit': ['q'],
    'query': ['y'],
    'page up': ['page up'],
    'page down': ['page down'],
    'help': ['?'],
    'shift column left': [',', '<'],
    'shift column right': ['.', '>'],
    'increase column width': ['=', '+'],
    'decrease column width': ['-'],
    'jump to last row': ['meta >'],
    'jump to first row': ['meta <'],
    'jump to numeric column': list('1234567890'),
    'jump to last column': ['ctrl e'],
    'jump to first column': ['ctrl a'],
    'name current table browser': ['n'],
    'switch to table browser': ['b'],
}

# on startup, verify no duplicate keybindings for developer sanity
__set_keybs = set()
for cmd, keybs in _commands.items():
    for keyb in keybs:
        if keyb in __set_keybs:
            print('Attempting to shadow keybinding ' + keyb + ' already in use.')
del __set_keybs


def set_keybindings_for_command(command, keybindings):
    """This helps avoid accidentally setting up keybindings that shadow each other"""
    global _commands
    # verify that it's not already in use...
    for cmd, keybs in _commands.items():
        if cmd != command:
            for keyb in keybs:
                if keyb in keybindings:
                    raise Exception('Attempting to shadow keybindings for ' + cmd)
    _commands[command] = keybindings

def keybs(command):
    return _commands[command][:] # so that you don't change the original list directly
