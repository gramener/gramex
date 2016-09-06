title: Gramex handles file uploads

`UploadHandler` lets you upload files and manage them. Here is a sample configuration:

    :::yaml
    url:
        uploadhandler:
            pattern: /$YAMLURL/upload
            handler: UploadHandler
            kwargs:
                path: $GRAMEXDATA/apps/guide/upload/    # ... save files here

Any file posted with a name of `file` is uploaded. Here is a sample HTML form:

    :::html
    <form action="upload" method="POST" enctype="multipart/form-data">
      <input name="file" type="file">
      <button type="submit">Submit</button>
      <input type="hidden" name="_xsrf" value="{{ handler.xsrf_token }}">
    </form>

(See the [XSRF](../filehandler/#xsrf) documentation to understand `xsrf_token`.)

<div class="example">
  <a class="example-demo" href="form">Try the uploader example</a>
  <a class="example-src" href="http://code.gramener.com/s.anand/gramex/tree/master/gramex/apps/guide/uploadhandler/form.html">Source</a>
</div>

After the file is uploaded, users can be redirected via the `redirect:` config
documented the [redirection configuration](../config/#redirection).

## Upload listing

You can retrieve the list of files uploaded via AJAX if you include a `methods:
GET` in the `kwargs:` section as follows:

    :::yaml
    url:
        uploadhandler:
            pattern: /$YAMLURL/upload
            handler: UploadHandler
            kwargs:
                path: $GRAMEXDATA/apps/guide/
                methods: get                   # GET /upload returns file info as JSON

The list of files uploaded can be retrieved from the [upload](upload) URL, along
with associated information:

<iframe src="upload"></iframe>

You can also retrieve the data in Python via `FileUpload(path).info()`.

    :::python
    import gramex.handlers.uploadhandler
    uploader = gramex.handlers.uploadhandler.FileUpload(path)
    return uploader.info()

The `uploader.info()` is a list of info objects with the following keys:

- **key**: A unique key representing the filename
- **filename**: Name of the uploaded file (as provided by the browser)
- **file**: Name of the file saved under the upload PATH
- **created**: Upload time in milliseconds since epoch (compatible with JavaScript's `new Date()`)
- **user**: User object, if the user had logged in when uploaded
- **size**: Size of the uploaded file in bytes
- **mime**: MIME type of the uploaded file
- **data**: A dictionary holding the form data sent along with the uploaded
  file. Keys are the form fields. Values are lists holding the submitted values.

## Upload deletion

To delete a file, submit a POST request to the UploadHandler with a `delete`
key. Here is a sample AJAX request:

    :::js
    var xsrf = {'X-Xsrftoken': cookie.get('_xsrf')}
    $.ajax('upload', {
      headers: xsrf,          // Set XSRF token
      method: 'POST',
      data: '{"delete": delete_key}'
    })


## Upload arguments

By default, `UploadHandler` uses the `file` query parameter to hold files, and
the `delete` query parameter to delete files. You can change that by specifying
a `keys:` configuration:

    :::yaml
    url:
        uploadhandler:
            pattern: ...
            handler: UploadHandler
            kwargs:
                path: ...
                keys:                     # Define what query parameters to use
                  file: [file, upload]    # Use <input id="file"> and/or <input id="upload">
                  delete: [del, rm]       # Use <input id="del"> and/or <input id="rm">

## Process uploads

`UploadHandler` accepts a `transform:` config that processes the files after they have been saved. For example:

    :::yaml
    url:
        uploadhandler:
            pattern: ...
            handler: UploadHandler
            kwargs:
                path: ...
                transform:
                    function: module.func     # Run module.func()
                    args: =content            # Optional: call with file metadata
                    kwargs: {}                # Optional: additional keyword args

This calls `module.func(file_metadata)` where `file_metadata` is an AttrDict with the keys mentioned in [Upload listing](#upload-listing). For example, this function will save CSV files as `data.json`:

    :::python
    def func(metadata):
        if metadata.mime == 'text/csv':
            path = os.path.join('... upload path ...', metadata.file)
            pd.read_csv(path).to_json('data.json')

The value returned by `module.func()` (if any) replaces `file_metadata`. This is stored in the UploadHandler's list of file metadata.
