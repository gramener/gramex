'Gramex file watch service'

import logging
from pathlib import Path
from collections import defaultdict
from orderedattrdict import AttrDict
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

handlers = AttrDict()
observer = Observer()
observer.start()


class FileEventHandler(FileSystemEventHandler):
    def __init__(self, paths=[], **events):
        super(FileEventHandler, self).__init__()

        self.paths = defaultdict(set)
        self.watches = []

        for path in paths:
            path = Path(path)
            if path.exists():
                path = path.resolve()
                self.paths[path.parent].add(str(path))

        self.__dict__.update(events)
        for directory, path in self.paths.items():
            self.watches.append(observer.schedule(self, str(directory)))

    def dispatch(self, event):
        result = any(event.src_path in paths for paths in self.paths.values())
        logging.info('%s: %s' % (result, event))
        if any(event.src_path in paths for paths in self.paths.values()):
            super(FileEventHandler, self).dispatch(event)

    def unschedule(self):
        for watch in self.watches:
            observer.unschedule(watch)


def watch(name, paths, **events):
    if name in handlers:
        handlers[name].unschedule()
    handlers[name] = FileEventHandler(paths, **events)
