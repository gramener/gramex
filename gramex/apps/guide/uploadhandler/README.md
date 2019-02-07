---
title: UploadHandler uploads files
prefix: UploadHandler
...

[TOC]

[UploadHandler][uploadhandler] lets you upload files and manage them. Here is a sample configuration:

```yaml
url:
  uploadhandler:
    pattern: /$YAMLURL/upload
    handler: UploadHandler
    kwargs:
      path: $GRAMEXDATA/apps/guide/upload/    # ... save files here
```

By default, `.meta.db` keystore is created in `kwargs:path` directory to store uploaded files' metadata.
You can configure `store` as follows:

```yaml
url:
  uploadhandler:
    pattern: /$YAMLURL/upload
    handler: UploadHandler
    kwargs:
      path: $GRAMEXDATA/apps/guide/upload/
      store:
        type: sqlite
        path: $GRAMEXDATA/apps/guide/upload/.fileinfo.db
        flush: 5
```

The `type:` can define any valid store type as seen in [session data](../auth/#session-data).

Note: Till **1.37**  `type: hdf5` was the default. From **1.38** onwards `type:sqlite` is defaulted.

Any file posted with a name of `file` is uploaded. Here is a sample HTML form:

```html
  <form action="upload" method="POST" enctype="multipart/form-data">
    <input name="file" type="file">
    <button type="submit">Submit</button>
    <input type="hidden" name="_xsrf" value="{{ handler.xsrf_token }}">
  </form>
```

(See the [XSRF](../filehandler/#xsrf) documentation to understand `xsrf_token`.)

<div class="example">
  <a class="example-demo" href="form">Try the uploader example</a>
  <a class="example-src" href="http://github.com/gramener/gramex/blob/master/gramex/apps/guide/uploadhandler/form.html">Source</a>
</div>

After the file is uploaded, users can be redirected via the `redirect:` config
documented the [redirection configuration](../config/#redirection).

## AJAX uploads

[DropZone](https://www.dropzonejs.com/) provides drag-and-drop AJAX uploads with
progress bars. For example:

```html
<link rel="stylesheet" href="ui/dropzone/dist/min/dropzone.min.css">
<form action="upload" class="dropzone"></form>
<script src="ui/dropzone/dist/min/dropzone.min.js"></script>
```

creates this box:

<link rel="stylesheet" href="../ui/dropzone/dist/min/dropzone.min.css">
<form action="upload" class="dropzone"></form>
<script src="../ui/dropzone/dist/min/dropzone.min.js"></script>

## Saving uploads

By default, the file is saved in the `path:` specified by `gramex.yaml`, with the
filename passed by the browser.

You can change the path where the file is saved using `<input name="save">`. See
the example below:

    :::html
    <form action="upload" method="POST" enctype="multipart/form-data">
      <input name="file" type="file">
      <button type="submit">Submit</button>
      <input type="hidden" name="save" value="folder/data.csv">
      <input type="hidden" name="_xsrf" value="{{ handler.xsrf_token }}">
    </form>

This saves the file under `folder/data.csv`, which is under the `path:` section
specified by `gramex.yaml`. `folder/` is created if required.

If multiple file uploads are present, multiple `save` fields can be used to
specify the filenames in order.

If the `save` value refers to a path outside of the `path:` specified, the
handler returns a HTTP 403.

To disable users from overwriting the filename, you can set `keys.save: []` in
`gramex.yaml`. See [Upload arguments](#upload-arguments)

## Overwriting uploads

If the [target location](#saving-uploads) already exists, there are 4 ways of
handling it. This is specified by the `overwrite:` key in `gramex.yaml`.

```yaml
    handler: UploadHandler
    kwargs:
      path: ...
      if_exists: error        # Raises a HTTP 403 with a reason saying "file exists"
      if_exists: backup       # Move the original to filename.YYYYMMDD-HHMMSS.ext
      if_exists: overwrite    # Overwrite the original without backup
      if_exists: unique       # Save to a new file: filename.1, filename.2, etc
```

## Upload listing

You can retrieve the list of files uploaded via AJAX if you include a `methods:
GET` in the `kwargs:` section as follows:

```yaml
url:
  uploadhandler:
    pattern: /$YAMLURL/upload
    handler: UploadHandler
    kwargs:
      path: $GRAMEXDATA/apps/guide/
      methods: get                   # GET /upload returns file info as JSON
```

The list of files uploaded can be retrieved from the [upload](upload) URL, along
with associated information:

<iframe class="w-100" src="upload"></iframe>

You can also retrieve the data in Python via `FileUpload(path).info()`.

```python
import gramex.handlers.uploadhandler
uploader = gramex.handlers.uploadhandler.FileUpload(path)
return uploader.info()
```

The `uploader.info()` is a list of info objects with the following keys:

- **key**: A unique key representing the filename
- **filename**: Name of the uploaded file (as provided by the browser)
- **file**: Relative path + filename of the file saved under the upload `path:`
- **created**: Upload time in milliseconds since epoch (compatible with JavaScript's `new Date()`)
- **user**: User object, if the user had logged in when uploaded
- **size**: Size of the uploaded file in bytes
- **mime**: MIME type of the uploaded file
- **data**: A dictionary holding the form data sent along with the uploaded
  file. Keys are the form fields. Values are lists holding the submitted values.

## Upload deletion

To delete a file, submit a POST request to the UploadHandler with a `delete`
key. Here is a sample AJAX request:

```js
$.ajax('upload', {
  method: 'POST',
  data: {'delete': file}  // Use the 'file' attribute in uploader.info()
})
```

## Upload arguments

By default, `UploadHandler` uses these form keys:

- `<input id="file" type="file">` is used to upload files
- `<input id="delete" value="file.ext">` is used to delete `file.ext`
- `<input id="save" value="path/uploaded.ext">` is used to save the file as `path/uploaded.ext`

You can change the keys used via the `keys:` configuration.

```yaml
url:
  uploadhandler:
    pattern: ...
    handler: UploadHandler
    kwargs:
      path: ...
      keys:                     # Define what query parameters to use
        file: [file, upload]    # Use <input id="file"> and/or <input id="upload">
        delete: [del, rm]       # Use <input id="del"> and/or <input id="rm">
        save: [save]            # Use <input id="save"> to specify the save location
```

To prevent users from changing or setting the filename, use:

```yaml
    keys:
      save: []    # No field names can override the user provided filename
```

## Process uploads

`UploadHandler` accepts a `transform:` config that processes the files after they have been saved. For example:

```yaml
url:
  uploadhandler:
    pattern: ...
    handler: UploadHandler
    kwargs:
      path: ...
      transform:
        function: module.func(meta, handler)
```

This calls `module.func(meta, handler)` where `meta` is an AttrDict with the
keys mentioned in [Upload listing](#upload-listing). For example, this function
will save CSV files as `data.json`:

```python
def func(meta, handler):
  if meta.mime == 'text/csv':
    path = os.path.join('... upload path ...', meta.file)
    pd.read_csv(path).to_json('data.json')
```

If `module.func()` returns a value, it replaces the file metadata. This allows
you to add / modify delete keys in the [Upload listing](#upload-listing).

If no `args` or `kwargs` are specified, the transform function is called with
`(meta, handler)` as the keyword arguments.

[uploadhandler]: https://learn.gramener.com/gramex/gramex.handlers.html#gramex.handlers.UploadHandler
