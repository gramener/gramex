---
title: File upload and processing
prefix: Tip
...

We can upload and process files with UploadHandler in Gramex:

HTML:

    :::html
    <form action="upload" method="POST" enctype="multipart/form-data" id="input-form">
      <legend>Gramex UploadHandler</legend>
      <div class="form-group">
        <input type="file" name="file" class="form-control" id="upload-files">
      </div>
      <input type="hidden" name="save" value="your_preferred_name.csv">
      <input type="hidden" name="_xsrf" value="{{ handler.xsrf_token }}">
      <button type="submit" class="btn btn-primary">Submit</button>
    </form>

gramex.yaml:

    :::yaml
    project/upload:
      pattern: /$YAMLURL/upload
      handler: UploadHandler
      kwargs:
        path: $YAMLPATH/uploads/    # ... save files here
        methods: get
        redirect:
          query: next
          url: /$YAMLURL/

This will save the file as `uploads/your_preferred_name.csv`.

If you want to process the file post upload, add transform attribute to the kwargs section:

    :::yaml
    transform:
      function: app.process_file(content, handler)

then use `process_file(content, handler)` in `app.py`.

More
====

- UploadHandler supports custom filename from early August - [dev](https://github.com/gramener/gramex/tree/dev) version.
- supports handling existing files - [overwriting uploads](../uploadhandler/#overwriting-uploads) section
- [delete files](../uploadhandler/#upload-deletion)
