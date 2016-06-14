# Gramex Update

The Gramex update app periodically receives logs from Gramex installations. It
saves these logs into an append-only [JSONL](http://jsonlines.org/) file located
at `$GRAMEXDATA/data/update/log.jsonl` via a TimedRotatingFileHandler.

It returns the latest Gramex version as a JSON response. The response looks like
this (for example):

    {"version": "1.2.3"}

This indicates that the latest semantic version is "1.2.3" and that clients
with a lower version should upgrade.
