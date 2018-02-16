'''
The file watch service uses `watchdoc <https://pythonhosted.org/watchdog/>`_ to
monitor files, and run functions when the file changes.
'''

import os
import six
import atexit
from fnmatch import fnmatch
from orderedattrdict import AttrDict
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from gramex.config import app_log

# Terminology:
#   observer    - a single instance class that has all scheduler related behavior
#   watch       - an instance that watches a single *folder*
#   handler     - an instance that handles events - associated with a single *name*

# There's only one observer. Start it at the beginning and schedule stuff later
observer = Observer()
observer.start()
atexit.register(observer.stop)

handlers = {}               # (handler, watch) -> (folder, name)
watches = AttrDict()        # watches[folder] = ObservedWatch

if six.PY2:
    PermissionError = RuntimeError


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
    # Create a series of schedules and handlers
    unwatch(name)

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
        _folder, watch = get_watch(folder, watches)
        # If a watch for this folder (or a parent) exists, use that folder's watch instead
        if watch is not None:
            observer.add_handler_for_watch(handler, watch)
            folder = _folder
        # If it's a new folder, create a new watch for it
        elif os.path.exists(folder):
            try:
                watch = watches[folder] = observer.schedule(handler, folder, recursive=True)
            except PermissionError:
                app_log.warning('No permission to watch changes on %s', folder)
                continue
        else:
            app_log.warning('watch directory %s does not exist', folder)
            continue
        # If EXISTING sub-folders of folder have watches, consolidate into this watch
        consolidate_watches(folder, watch)
        # Keep track of all handler-watch associations
        handlers[handler, watch] = (folder, name)
    release_unscheduled_watches()


def unwatch(name):
    '''
    Removes all handler-watch associations for a watch name
    '''
    for (_handler, _watch), (_folder, _name) in list(handlers.items()):
        if _name == name:
            del handlers[_handler, _watch]
            observer.remove_handler_for_watch(_handler, _watch)


def get_watch(folder, watches):
    '''
    Check if a folder already has a scheduled watch. If so, return it.
    Else return None.
    '''
    for watched_folder, watch in watches.items():
        if folder.startswith(watched_folder):
            return watched_folder, watch
    return None, None


def consolidate_watches(folder, watch):
    '''If folder is a parent of watched folders, migrate those handlers to this watch'''
    for (_handler, _watch), (_folder, _name) in list(handlers.items()):
        if _folder.startswith(folder) and _folder != folder:
            del handlers[_handler, _watch]
            observer.remove_handler_for_watch(_handler, _watch)
            handlers[_handler, watch] = (folder, _name)
            observer.add_handler_for_watch(_handler, watch)


def release_unscheduled_watches():
    watched_folders = {folder for folder, name in handlers.values()}
    for folder, watch in list(watches.items()):
        if folder not in watched_folders:
            observer.unschedule(watch)
            del watches[folder]
