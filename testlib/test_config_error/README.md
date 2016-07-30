This is a work-in-progress test case. It ensures that errors in `gramex.yaml`
without Gramex terminating.

For now, run Gramex here are expect the following errors:

    url:log_not_dict.log must be a dict with a format key
    url:log_no_format.log must be a dict with a format key
    url:log_format_not_string.log.format invalid: 1
    url:log_format_invalid.log.format invalid: %0
    url:log_format_unknown.log.format invalid: %(nonexistent)

**TODO**: automate this test
