from . import event_listeners, commands

for module in (event_listeners, commands):
    module.setup()
