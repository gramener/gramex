---
title: Logins for apps on UAT
prefix: Tip
...

The majority of our projects are now hosted on <https://uat.gramener.com/monitor/apps>

From now on, the page also displays the login IDs and passwords for these apps.

To add this to your project, add a **test:** section to your **gramex.yaml**.

    :::yaml
    test:
      auth:
        user: test-user-name
        password: test-user-password

This will automatically add the login and password on the UAT page.

Here's an [example](https://code.gramener.com/swathi.yegireddi/BARC-Advertising/blob/c1daad68/gramex.yaml#L9).

You can add multiple users and passwords as a list. Here's the [documentation](https://learn.gramener.com/wiki/dev.html#deploying).
