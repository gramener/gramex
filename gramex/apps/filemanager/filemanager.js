/* eslint-env browser, jquery */
/* globals moment, _ */

(function () {
  // Expose $(el).filemanager(options).
  // Options are the same as $().formhandler()
  $.fn.filemanager = function (opts) {
    // Create a copy of options, overriding default options
    let newopts = Object.assign({}, DEFAULT_OPTS, opts)
    // If the user uses a pre-defined column name, set default attributes for it.
    // e.g. if the user just says `{name: 'size'}`, add an `editable: false` to it.
    newopts.columns.forEach(col => {
      if (_.has(COLMAP, col.name))
        _.defaults(col, COLMAP[col.name])
    })
    // For each element selected, render a FormHandler table.
    // renderTable modifies column links in the options, so clone options to avoid interference.
    this.each(function () {
      renderTable(this, _.cloneDeep(newopts))
    })
  }

  // move it inside filemanager
  function renderTable(el, opts) {
    let filecol = _.find(opts.columns, c => c.name == 'file')
    if (filecol)
      filecol.link = filecol.link || el.dataset.src + '?id=<%- row.id %>&_download'
    $(el).on('load', function () {
      let btn = $(this).find('.uploadbtn').get(0)
      attach_dropzone(btn, el, el.dataset.src, true, renderTable.bind(this, el, opts))
      // Attach a dropzone to the whole element
      attach_dropzone(el, el, el.dataset.src, false, renderTable.bind(this, el, opts))
    }).formhandler(opts)
  }

  function attach_dropzone(el, parent, url, clickable = true, success = null) {
    try {
      $(el).dropzone({
        url: url,
        clickable: clickable,
        createImageThumbnails: false,
        previewTemplate: '<div></div>',
        init: function () {
          this.on('success', success) // function(e) { renderTable(parent, opts) })
            .on('error', $(parent).data('formhandler').failHandler)
        }
      })
    } catch (err) { if (err.message != 'Dropzone already attached.') throw err }
  }

  const DEFAULT_OPTS = {
    edit: true,
    columns: [
      { name: 'file', title: 'File', editable: { input: 'text' } },
      { name: 'size', title: 'Size', type: 'number', editable: false },
      { name: 'mime', title: 'Type', editable: false },
      {
        name: 'date',
        title: 'Date',
        type: 'date',
        format: function (d) {
          return moment.duration(moment().diff(moment.unix(d.value))).humanize() + ' ago'
        },
        editable: false
      },
      {
        name: 'delete',
        title: 'Delete',
        template: '<td><button class="btn btn-danger" data-action="delete">&times;</button></td>',
        editable: false
      },
      { name: 'tags', title: 'Tags', editable: { input: 'text' } }
    ],
    exportTemplate: '<button class="uploadbtn btn btn-primary">Upload</button>'
  }

  const COLMAP = _.keyBy(DEFAULT_OPTS.columns, 'name')
})()
