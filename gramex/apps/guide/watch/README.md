title: Gramex watches files

The `watch:` section in [gramex.yaml](../gramex.yaml) triggers events when files are modified. For example:

    :::yaml
    watch:                                  # Define files to watch
        data-files:                         # Create a watched named data-files
            paths:                          # Watch for these files
                - $YAMLPATH/dir/            # - any file under the dir/ subdirectory
                - $YAMLPATH/*.txt           # - any CSV file under this folder
                - $YAMLPATH/data.csv        # - data.csv in this folder
                - data.xslx                 # - data.xlsx from where Gramex was started
            on_modified: module.function    # When file is changed, call module.function(event)

Each named watch has the following keys:

- `paths`: a list of files, directories or wildcards to watch for
- `on_modified`: called when the file is modified
- `on_created`: called when the file is created
- `on_deleted`: called when the file is deleted
- `on_moved`: called when the file is moved
- `on_any_event`: called for any change in the file

The event handler functions are called with a single argument `event`. The
`event` is a [watchdog event][event]. Is has the following attributes:

- `event.src_path`: the path that triggered the event
- `event.is_directory`: True if the path is a directory
- `event.event_type`: type of the event.

Here is a sample event handler that prints the event:

    :::python
    def watch_file(event):
        print(event.src_path, event.is_directory, event.event_type)


## Watching files

Your functions can watch files efficiently. For example, this code will run
`log()` when `filename.txt` is created, deleted or modified. `log()` will be called with a 
`event` is a [watchdog event][event].


    :::python
    from gramex.services.watcher import watch

    def log(event):
        print(event)

    watch(name='unique-name', paths=['filename.txt'],
          on_created=log, on_deleted=log, on_modified=log)

[event]: http://pythonhosted.org/watchdog/api.html#module-watchdog.events
