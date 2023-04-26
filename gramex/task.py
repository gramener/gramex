'''Task management utilities'''
from typing import Union


def add(queue: str, task: Union[str, list, dict], type: str = 'shell', **kwargs):
    import datetime
    import gramex.data
    import json

    return gramex.data.insert(
        **gramex.service.storelocations.task,
        args={
            "timestamp": [datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%fZ')],
            "queue": [queue],
            "type": [type],
            "task": [json.dumps(task)],
            "status": ["pending"],
            "info": [""],
            "output": [""],
        },
        id=["timestamp"],
    )


def schedule(queue: str, max_tasks: int = 8, **kwargs) -> None:
    '''To execute tasks in a queue, add this to `gramex.yaml`:

    ```yaml
    schedule:
      gramex-task-$*:
        function: gramex.task.schedule(queue='my-queue-name', max_tasks=10)
        every: 2 minutes
    ```

    Now any task added via `gramex.task.add(...)` will be auto-executed.

    Parameters:

        queue: task queue name to execute. fnmatch-style wildcards are allowed.
          E.g. `"x.*"` matches x.a, x.b, etc.
        max_tasks: number of tasks allowed concurrently. Tasks queue up until a slot is available.
    '''
    import gramex
    import gramex.data

    # TODO: If processes that ought to be running in this system are not, make them pending
    # running = gramex.data.filter(
    #     **gramex.service.storelocations.task, args={"status": ["running"], "_sort": "timestamp"}
    # )
    # TODO: Count running processes. Exit if >= max_tasks
    # TODO: While running processes < max_tasks, get next pending process and run it


def run(timestamp: str, queue, type: str, task: str):
    import sys

    if type == 'shell':
        import subprocess

        process = subprocess.Popen(
            [sys.executable, '-timestamp', timestamp, '-queue', queue, '-task', task, '-table': ..., '-url': ...],
            # TODO: Detach subprocess on Linux/Mac: https://stackoverflow.com/a/64145368/100904
            # TODO: Detach subprocess on Windows: https://stackoverflow.com/a/52450172/100904
        )
        pid = process.pid
        # TODO: update the "info" and "status" in the DB
        # __update(db, params={"pid": pid, "status": "running"}, condition=f"id={job2run['id']}")
    else:
        raise ValueError(f'Unknown task type: {queue}.{type}')


def commandline(args=None):
    import json
    import gramex
    import subprocess
    import sys

    args = gramex.parse_command_line(sys.argv[1:] if args is None else args)
    task = json.parse(args.task)
    if isinstance(task, str):
        args, kwargs = [task], {'shell': True}
    elif isinstance(task, list):
        args, kwargs = task, {}
    elif isinstance(task, dict):
        args, kwargs = task['args'], task['kwargs']
    else:
        raise ValueError(f'Task must be str, list, dict. Not {type!r}')

    kwargs['capture_output'] = True
    # TODO: Re-implement using subprocess.run.
    process = subprocess.run(*args, **kwargs)
    stdout, stderr = process.communicate()
    return_code = process.returncode
    status = "success" if return_code == 0 else "error"
    output = json.dumps(
        {
            "stdout": stdout.decode("utf-8"),
            "stderr": stderr.decode("utf-8"),
            "return_code": returncode,
        }
    )
    gramex.data.update(
        url=args.url,
        table=args.table,
        params={"pid": 0, "status": status, "output": output},
        condition=f"timestamp={args.timestamp}",
    )
