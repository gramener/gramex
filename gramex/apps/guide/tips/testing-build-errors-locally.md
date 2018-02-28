---
title: Testing build errors locally
prefix: Tip
...

To test build errors locally, set it up using:

    :::shell
    pip install -e flake8-gramex
    npm install -g eslint@2.6.0 eslint-plugin-template htmllint-cli jscpd

Make sure you have `.flake8`, `.eslintrc` and `.htmllintrc` from `yo gramex`. Then run:

    :::shell
    flake8
    eslint --ext js,html .
    htmllint

This will test most build errors. But if you want to test them all, another approach is:

- Push a new branch and test build errors
- Fix them on that branch and keep testing
- When done, merge the new branch into your dev branch using `git merge --squash new-branch`

This is documented on [Wiki](https://learn.gramener.com/wiki/dev.html).
