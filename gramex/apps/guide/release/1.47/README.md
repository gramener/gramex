---
title: Gramex 1.47 Release Notes
prefix: 1.47
...

[TOC]

## g1

gramex [uicomponents](../../uicomponents) now ships with [`g1`](https://code.gramener.com/cto/g1) `0.11.0`

In this version, two new interaction components are released.

### $.urlchange

[$.urlchange](https://code.gramener.com/cto/g1#urlchange) acts as an event listener for URL hash changes.
triggered by [$.urlfilter](https://code.gramener.com/cto/g1#urlfilter) --
This makes it easy to build URL-driven applications.

Suppose we have buttons that sort based on "City" or "Sales".

DOM events should change the URL like this:

```html
<button href="?_sort=City" class="urlfilter" target="#">City</button>
<button href="?_sort=Sales" class="urlfilter" target="#">Sales</button>
<script>
  $('body').urlfilter()
</script>
```

Now, changes in the URL should trigger actions:

```javascript
$(window)
  .urlchange()    // URL changes trigger '#?city' events
  .on('#?city', function(e, city) { action(city) })
```

[Read documentation](https://code.gramener.com/cto/g1#urlchange)

### $.ajaxchain

[$.ajaxchain()](https://code.gramener.com/cto/g1#ajaxchain) chains AJAX requests, loading multiple pages in sequence

### $.template

[$.template](https://code.gramener.com/cto/g1#template) can append to existing DOM elements,
allowing AJAX requests to add to a list rather than replace them

## UI Components

New UI classes are added

- [border](../../uicomponents/#border) - `.border-2` for a border twice as thick.
    - Similarly, `border-top-1`, `border-right-1`, `border-bottom-1`, `border-left-1` add a `1px` border on each side.
- [overflow](../../uicomponents/#overflow) - `.overflow-hidden`, `.overflow-auto` and `.overflow-scroll` set the overflow styles.
- [text-decoration](../../uicomponents/#text-decoration) - `.text-decoration-none` removes the text-decoration.
- [cursor](../../uicomponents/#cursor) - `.cursor-default` helps when you make clickable elements non-clickable.
    - `.pointer-events-none` sets the pointer-events to none

## Auth

You can now protect all pages (handlers) at a single place.

To add access control to the entire application, use:

```yaml
handlers:
  BaseHandler:
    # Protect all pages in the application. All auth: configurations allowed
    auth:
      login_url: /$YAMLPATH/login/
```

This is the same as adding the `auth: ...` to every handler in the application.

[Read more](../../auth/#protect-all-pages)

## Guide

We've re-ordered and grouped [Gramex Guide](../../) index sidebar into logical heading.

## Stats

- Code base: 29,028 lines (python: 17,428, javascript: 1,852, tests: 9,748)
- Test coverage: 78%

## Upgrade

Note: `gramex >= 1.41` onwards requires `Anaconda >= 5.2.0`

To upgrade Gramex, run:

```bash
pip install --verbose gramex==1.47
```

To upgrade apps dependencies, run:

```bash
gramex setup --all
```

This downloads Chromium and other front-end dependencies. That may take time.
