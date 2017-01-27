'''
The file watch service uses `watchdoc <https://pythonhosted.org/watchdog/>`_ to
monitor files, and run functions when the file changes.
'''

import os
import atexit
from fnmatch import fnmatch
from orderedattrdict import AttrDict
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from gramex.config import app_log

# There's only one observer. Start it at the beginning and schedule stuff later
observer = Observer()
observer.start()
atexit.register(observer.stop)

handlers = AttrDict()       # handler[name] = FileEventHandler
watches = AttrDict()        # watches[directory] = ObservedWatch


class FileEventHandler(FileSystemEventHandler):
    '''
    Each FileEventHandler is associated with a set of events from a config.
    It maps a set of paths to these events.
    '''
    def __init__(self, patterns, **events):
        super(FileEventHandler, self).__init__()
        self.patterns = patterns
        self.__dict__.update(events)

    def dispatch(self, event):
        path = os.path.abspath(event.src_path)
        if any(fnmatch(path, pattern) for pattern in self.patterns):
            super(FileEventHandler, self).dispatch(event)


def watch(name, paths, **events):
    '''
    Watch one or more paths, and trigger an event function.

    Example::

        watch('test', ['test.txt'],
              on_modified: lambda event: logging.info('Modified test.txt'),
              on_created: lambda event: logging.info('Created test.txt'))

    When ``test.txt`` is modified or created, it logs one of the above messages.

    To replace the same handler with another, use the same ``name``::

        watch('test', ['test.txt'],
              on_deleted: lambda event: logging.info('Deleted test.txt'))

    Now, when ``test.txt`` is deleted, it logs a message. But when ``test.txt``
    is created or modified, no message is shown, since the old handler has been
    replaced.

    To remove this watch, call ``unwatch('test')``.

    :arg string name: Unique name of the watch.  To replace an existing watch,
        re-use the same name.
    :arg list paths: List of relative or absolute paths to watch.  The paths
        can be strings or ``pathlib.Path`` objects.
    :arg function on_modified(event): Called when any path is modified.
    :arg function on_created(event): Called when any path is created.
    :arg function on_deleted(event): Called when any path is deleted.
    :arg function on_moved(event): Called when any path is moved.
    :arg function on_any_event(event): Called on any of the above events.
    '''
    # if name in handlers:
    #     handlers[name].unschedule()
    # handlers[name] = FileEventHandler(paths, **events)

    # Create a series of schedules and handlers
    if name in handlers:
        unwatch(name)
    handlers[name] = []

    patterns = set()        # List of absolute path patterns
    folders = set()         # List of folders matching these paths
    for path in paths:
        # paths can be pathlib.Path or str. Convert to str before proceeding
        path = os.path.abspath(str(path))
        if os.path.isdir(path):
            patterns.add(os.path.join(path, '*'))
            folders.add(path)
        else:
            patterns.add(path)
            folders.add(os.path.dirname(path))

    handler = FileEventHandler(patterns, **events)

    for folder in folders:
        if folder in watches:
            observer.add_handler_for_watch(handler, watches[folder])
        elif os.path.exists(folder):
            watches[folder] = observer.schedule(handler, folder, recursive=True)
        else:
            app_log.warning('watch directory %s does not exist', folder)
            continue
        handlers[name].append(AttrDict(name=name, handler=handler, watch=watches[folder],
                                       folder=folder))


def unwatch(name):
    '''
    Removes a named watch.
    '''
    for info in handlers.pop(name, []):
        observer.remove_handler_for_watch(info.handler, info.watch)
