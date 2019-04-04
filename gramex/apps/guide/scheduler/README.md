---
title: Schedule tasks
prefix: Scheduler
...

[TOC]

The `schedule:` section in [gramex.yaml](gramex.yaml.source) lets you run tasks on
startup or at specific times. Here are some sample uses:

- email insights every Wednesday
- data refresh every 4 hours
- post a tweet at 7:15 am every day

Here is a sample configuration:

```yaml
schedule:
    run-on-startup:
        function: logging.info(msg="Scheduled msg (on startup)")
        startup: true
    run-every-hour:
        function: schedule_utils.log_time   # Log the current time
        minutes: 0
        hours: '*'
```

Each named schedule section has the following keys:

- `function`: the function or expression to run (**required**)
- `args` and `kwargs`: the positional and keyword arguments to pass to the
  function. The function will be called as `function(*args, **kwargs)`. These
  are optional -- the function will by default be called as `function()`.
- `startup`: set this to true to run the function once at startup.
  Set this to `'*'` to run the function every time the config changes.
- `thread`: set this to true to run in a separate thread (if available.)

## Schedule timing

In addition, the schedule is specified via the `minutes`, `hours`, `dates`, `weekdays`, `months` and `years` keys.

- Any of these 6 fields may be an asterisk (*). This would mean the entire range
  of possible values, i.e. each minute, each hour, etc.
- Any field may contain a list of values separated by commas, (e.g. `1,3,7`) or
  a range of values (e.g. `1-5`).
- After an asterisk (*) or a range of values, you can use slash `/` to specify
  that values are repeated periodically. For example, you can write `0-23/2` in
  `hours:` to indicate every two hours (it will have the same effect as
  `0,2,4,6,8,10,12,14,16,18,20,22`); value `*/4` in `minutes:` means that the
  action should be performed every 4 minutes, `1-10/3` means the same as
  `1,4,7,10`.
- In `months:` and `weekdays:`, you can use names of months or days of weeks
  abbreviated to first three letters ("Jan,Feb,...,Dec" or "Mon,Tue,...,Sun")
  instead of their numeric values. Case does not matter.

## Schedule examples

For example, this configuration runs at on the 15th and 45th minute every 4 hours
on the first and last day of the month (if it's a weekday) in 2016-17.

```yaml
schedule:
  run-when-i-say:
    function: schedule_utils.log_time()
    minutes: '15, 45'           # Every 15th & 45th minute
    hours: '*/4'                # Every 4 hours
    dates: '1, L'               # On the first and last days of the month
    weekdays: 'mon-fri'         # On weekdays
    months: '*'                 # In every month
    years: '2016, 2017'         # the next 2 years
```

This configuration runs only on startup:

```yaml
schedule:
  run-on-startup:
    function: schedule_utils.log_time()
    startup: true
```

This configuration runs on startup, and re-runs every time the YAML file changes:

```yaml
schedule:
  run-on-startup:
    function: schedule_utils.log_time()
    startup: '*'
```

This configuration runs every hour on a separate thread:

```yaml
schedule:
  run-every-hour:
    function: schedule_utils.log_time()
    hours: '*'
    thread: true
```

The scheduler uses the local time zone of the server Gramex runs on. To run on
[UTC](https://en.wikipedia.org/wiki/Coordinated_Universal_Time) (i.e. GMT), add
`utc: true`:

```yaml
schedule:
  run-on-utc-schedule:
    function: schedule_utils.log_time()
    hours: 5            # Run at 5am UTC
    utc: true
```


## Scheduler preview

You can run schedules manually using the
[Admin Schedule](../admin/#admin-schedule) component at
[/admin/schedule](../admin/admin/schedule).


## Scheduler API

You can run an existing scheduler programmatically. This code runs the schedule
named `run-when-i-say`.

```python
from gramex import service      # Available only if Gramex is running
gramex.service.schedule['run-when-i-say'].run()
```

If it has a schedule, `.run()` will clear past schedules and set up a new
schedule.

You can create or update a scheduler dynamically. For example, this
FunctionHandler changes a schedule based on the URL's `?minutes=` parameter:

```python
from gramex.services.scheduler import Task

def update_schedule(handler):
    from gramex import service      # Available only if Gramex is running
    # If our scheduler is already set up, stop it first
    if 'custom-schedule' in service.schedule:
        service.schedule['custom-schedule'].stop()
    # Create a new scheduler with this configuration
    schedule = AttrDict(
        function=scheduler_method,            # Run this function
        minutes=handler.get_arg('minutes'),   # ... based on the URL's ?minutes=
    )
    # Set up the scheduled task. This will at the minute specified by ?minutes=
    service.schedule['custom-schedule'] = Task(
        'custom-schedule', schedule, service.threadpool)
```
