---
title: Reuse YAML configurations via anchors
prefix: Tip
...

`YAML` has a feature called ANCHORS that lets you re-use sections without copy-pasting.

For example, if you use the same `auth:` section or `error:` section in multiple handlers, you don't need to copy-paste the configuration. Just include a reference.

Here's an example

    :::yaml
	url1:
	  kwargs: ...
	    auth: &GRAMENER_AUTH      # & defines an anchor called GRAMENER_AUTH
	      membership:
	        hd: [gramener.com]
	url2:
	  kwargs: ...
	    auth: *GRAMENER_AUTH      # * re-uses the GRAMENER_AUTH anchor

This is documented at [https://learn.gramener.com/guide/config/#reusing-configurations](https://learn.gramener.com/guide/config/#reusing-configurations)

You can read a bit more about anchors at [http://camel.readthedocs.io/en/latest/yamlref.html#anchors](http://camel.readthedocs.io/en/latest/yamlref.html#anchors)
