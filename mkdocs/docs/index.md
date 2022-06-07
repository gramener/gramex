# Introduction

Gramex is a web server for data-driven applications. [Read the Gramex Guide for more information](https://gramener.com/gramex/guide/).

Running `gramex` on the command line calls these functions in order:

1. [gramex.commandline][] to parse the command line
2. [gramex.init][] to parse the [`gramex.yaml` config file][gramex.config]
3. [gramex.services][] to start individual services
