---
title: Conditions in gramex.yaml
prefix: Tip
...

Gramex dev branch supports if-conditions in YAML.

This is [documented here](../config/#conditions)

Sample uses:

1. Have a different authentication method in production server vs dev server
2. Have a different logging levels when running on different ports (e.g. port 9988 for testing, 9999 for deployment)
