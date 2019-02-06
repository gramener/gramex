---
title: Conditional Configurations in Gramex 1.x
prefix: Tip
...

The dev branch supports [conditional YAML variables](../config/#conditions).

If you want to have a different auth in [uat.gramener.com](https://uat.gramener.com), a different auth on your local machine, and a different auth in production, see below.

    :::yaml
    auth if 'win' in sys.platform:
        pattern: /login
        handler: IntegratedAuth

    auth if 'win' not in sys.platform:
        pattern: /login
        handler: LDAPAuth

The "... if ..." syntax is just a Python expression. On Windows, it will use the first paragraph as "auth". Non-Windows will use the second.

This will be available from 1.23, but you can start using it with the [dev branch](https://github.com/gramener/gramex/tree/dev/) right away.
