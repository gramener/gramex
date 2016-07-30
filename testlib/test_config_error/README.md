This is a work-in-progress test case. It ensures that errors in `gramex.yaml`
without Gramex terminating.

For now, run Gramex here are expect the following errors:

    url:log_not_dict.log is not a dict with a format key
    url:log_no_format.log is not a dict with a format key
    url:log_format_not_string.log.format invalid: 1
    url:log_format_invalid.log.format invalid: %0
    url:log_format_unknown.log.format invalid: %(nonexistent)
    url.error_no_keys.error code a is not a number (100 - 1000)
    url.error_no_keys.error code 1 is not a number (100 - 1000)
    url.error_no_keys.error code 1001 is not a number (100 - 1000)

**TODO**: automate this test
