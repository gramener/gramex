---
title: VSCode Extension
prefix: Extension
...

## Installation

- This extension is available on [Visual Studio](https://code.visualstudio.com/). Install version `1.31` or later.
- In `Activity Bar` under `Extensions` tab search for `Gramex Snippets`. Alternatively, you can find the extension on [VSCode Marketplace](https://marketplace.visualstudio.com/items?itemName=gramener.gramexsnippets).

## How to use

In `gramex.yaml` or any `.yaml` file, type `grx-form`... it should prompt two `FormHandler` related snippets as suggestions. If you do not see auto suggestion, see [how to resolve](#yaml-auto-suggestions-bug-in-vscode) this below.

Supported snippet commands: `grx-filehandler`, `grx-formhandler_db`, `grx-formhandler_csv`, `grx-email`, `grx-custom_session`, `grx-custom_log`, `grx-cache_assets`, `grx-auth_db`, `grx-auth_google`, `grx-auth_simple`.

## Features

Features as of version `1.2.0`:

- `FileHandler` endpoint
- `FormHandler` flat files and database endpoints
- `auth` endpoints
- Custom `log` and `session` configurations
- `email` service
- Caching assets

Visit Marketplace to get the latest feature list.

### YAML auto-suggestions bug in VSCode

There appears to be a [bug in VSCode](https://github.com/Microsoft/vscode/issues/27095) in autosuggesting YAML snippets. A workaround solution is to do as below:

- In VSCode `Preferences -> Settings`, search and find `Quick Suggestions`
- Click `edit in settings.json` and add the below

```JSON
    "editor.quickSuggestions": {
        "other": true,
        "comments": false,
        "strings": true
    }
```

## Changelog

- [CHANGELOG](https://github.com/gramener/gramexsnippets/blob/master/CHANGELOG.md) maintains release-wise changes

## Bugs

- Report bugs on [gramexsnippets](https://github.com/gramener/gramexsnippets/issues) repository
