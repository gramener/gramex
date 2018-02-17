---
title: Different configurations for different machines
prefix: Tip
...

Gramex 1.23 lets you set up [different configurations](https://learn.gramener.com/guide/config/#conditions) for different machines.

For example, this sets up different authentications based on the machine name:

	:::yaml
	auth if socket.gethostname() == 'uat':  # on uat.gramener.com
	    pattern: /login
	    handler: LDAPAuth
	auth if 'win' in sys.platform:          # on any Windows machine
	    pattern: /login
	    handler: IntegratedAuth
	auth if HOME.startswith('D:')           # If running on D: drive
	    ...

If `if` is present in any key, the portion after if is evaluated as a Python expression. All [YAML variables](https://learn.gramener.com/guide/config/#yaml-variables) are available as Python variables.

Conditions are evaluated in order. The **last applied condition** is used.

Please feel free to use this to set up different configurations (e.g. authentication, logging) across different systems.
