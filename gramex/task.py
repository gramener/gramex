"""Task management utilities"""
from typing import Union
import gramex


def __update(db, table, params, condition):
    query = (
        f"UPDATE {table} SET "
        f"""{', '.join([f"{k}='{v}'" for k, v in params.items()])} """
        f"WHERE {condition} "
    )
    print("QUERY: ", query)
    import sqlalchemy as sa
    with sa.create_engine(db).connect() as conn:
        conn.execute(query)


def __set_status(db, status: str, timestamp: str):
    __update(
        db["url"],
        db["table"],
        params={"status": status},
        condition=f"timestamp='{timestamp}'",
    )
    # gramex.data.update(
    #     **gramex.service.storelocations.task,
    #     args={"status": [status], timestamp: [timestamp]},
    #     timestamp="timestamp",
    # )


def __get_next_enqueued(db) -> dict or None:
    failed = gramex.data.filter(**db, args={"status": ["error"], "_sort": "id", "_limit": [1]})
    if len(failed) > 0:
        return failed.iloc[0]

    pending = gramex.data.filter(**db, args={"status": ["pending"], "_sort": "id", "_limit": [1]})
    if len(pending) > 0:
        return pending.iloc[0]

    return None


def add(queue: str, task: Union[str, list, dict], type: str = "shell", **kwargs):
    import datetime
    import gramex.data
    import gramex.services
    import json
    gramex.app_log.warning("runnign something, i dont know what")
    print(gramex.service.storelocations.task)
    return gramex.data.insert(
        **gramex.service.storelocations.task,
        args={
            "timestamp": [datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%fZ")],
            "queue": [queue],
            "type": [type],
            "task": [task],
            "status": ["pending"],
            "info": [""],
            "output": [""],
        },
        id=["timestamp"],
    )


def schedule(queue: str, max_tasks: int = 8, **kwargs) -> None:
    """To execute tasks in a queue, add this to `gramex.yaml`:

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
    """
    import gramex
    import gramex.data
    import json
    import os

    running = gramex.data.filter(
        **gramex.service.storelocations.task, args={"status": ["running"], "_sort": "timestamp"}
    )
    running_count = 0
    for _, job in running.iterrows():
        print(job)
        info = json.loads(job["info"])
        pid = info.get("pid", 0)
        if not os.path.exists(os.path.join(f"/proc/{pid}/status")):
            __set_status(gramex.service.storelocations.task, "pending", job.timestamp)
            continue
        with open(f"/proc/{pid}/status", "r") as f:
            if job["task"] not in f.read():
                __set_status(gramex.service.storelocations.task, "pending", job.timestamp)
                continue

        running_count += 1
        running.drop(job.timestamp, inplace=True)

    if running_count >= max_tasks:
        return

    next_job = __get_next_enqueued(gramex.service.storelocations.task)
    if next_job is not None:
        __run(next_job.timestamp, next_job.queue, next_job.type, next_job.task)


def __run(timestamp: str, queue, type: str, task: str):
    import sys
    import os
    import subprocess
    import json

    if type not in ["shell"]:
        raise ValueError(f"Unknown task type: {queue}.{type}")

    cmd = [
        'gramex',
        'task',
        '-timestamp',
        f'"{timestamp}"',
        '-queue',
        f'"{queue}"',
        '-task',
        task,
        '-url',
        f'''"{gramex.service.storelocations.task['url']}"''',
        '-table',
        f'''"{gramex.service.storelocations.task['table']}"''',
    ]
    print("cmd : "," ".join(cmd))
    # TODO: Detach subprocess on Linux/Mac: https://stackoverflow.com/a/64145368/100904
    # TODO: Detach subprocess on Windows: https://stackoverflow.com/a/52450172/100904
    osname = os.name 
    if osname == "nt":
        flags = 0
        flags |= 0x00000008  # DETACHED_PROCESS
        flags |= 0x00000200  # CREATE_NEW_PROCESS_GROUP
        flags |= 0x08000000  # CREATE_NO_WINDOW
        pkwargs = {
            "close_fds": True,  # close stdin/stdout/stderr on child
            "creationflags": flags,
        }
    elif osname == "posix":
        pkwargs = {"start_new_session": True}
    else:
        raise ValueError(f"Unsupported OS: {osname}")
    
    process = subprocess.Popen(cmd, **pkwargs)
    pid = process.pid
    __update(
        gramex.service.storelocations.task["url"],
        gramex.service.storelocations.task["table"],
        params={"info": json.dumps({"pid": pid}), "status": "running"},
        condition=f"timestamp='{timestamp}'",
    )
    # gramex.data.update(
    #     **gramex.service.storelocations.task,
    #     args={"timestamp": [timestamp], "status": ["running"]},
    #     id=timestamp,
    # )


def commandline(args=None):
    with open("somesomesome.txt", "a") as f:
        f.write("running task")
    import json
    import gramex
    import subprocess
    import sys

    # args = gramex.parse_command_line(sys.argv[1:] if args is None else args)
    task = args['task']
    url = args['url']
    table = args['table']
    timestamp = args['timestamp']
    # timestamp = args['timestamp'].strftime("%Y-%m-%d %H:%M:%S.%fZ")
    if isinstance(task, str):
        args, kwargs = [task], {"shell": True}
    elif isinstance(task, list):
        args, kwargs = task, {}
    elif isinstance(task, dict):
        args, kwargs = task["args"], task["kwargs"]
    else:
        with open("somsomsomsom.txt", "w") as f:
            f.write(f"Task must be str, list, dict. Not {type!r}")
        raise ValueError(f"Task must be str, list, dict. Not {type!r}")

    kwargs["capture_output"] = True
    process = subprocess.run(*args, **kwargs)
    return_code = process.returncode
    status = "success" if return_code == 0 else "error"
    output = json.dumps(
        {
            "stdout": process.stdout.decode("utf-8"),
            "stderr": process.stderr.decode("utf-8"),
            "return_code": return_code,
        }
    )
    __update(
        url,
        table,
        {"status": status, "output": output, "info": json.dumps({"pid": 0})},
        f"timestamp='{timestamp}'",
    )
    # gramex.data.update(
    #     url=args.url,
    #     table=args.table,
    #     params={"pid": 0, "status": status, "output": output},
    #     condition=f"timestamp={args.timestamp}",
    # )
