/* eslint-env browser, jquery */
/* globals moment, _ */

const DOWNLOAD_LINK = '?id=<%- row.id %>&_format=file&_download'
const DEFAULT_OPTS = {
  edit: true,
  columns: [
    {
      name: 'file', // link: `${url}`,
      editable: {
        input: 'text'
      }
    },
    {name: 'size', editable: false},
    {name: 'mime', editable: false},
    {
      name: 'date',
      format: function(d) {
        return moment.duration(moment().diff(moment.unix(d.value))).humanize() + ' ago'
      },
      editable: false
    },
    {
      name: 'Delete',
      template: '<td><button class="btn btn-danger" data-action="delete">&times;</button></td>',
      editable: false
    },
    {name: 'tags', editable: {input: 'text'}},
  ],
  exportTemplate: '<button id="uploadbtn" class="btn btn-primary">Upload</button>'
}

const DEFAULT_COLS = _.map(DEFAULT_OPTS.columns, 'name')

function attach_dropzone(el, parent, url, clickable = true, success = null) {
  try {
    $(el).dropzone({
      url: url,
      clickable: clickable,
      createImageThumbnails: false,
      previewTemplate: '<div></div>',
      init: function() {
        this.on('success', success) // function(e) { renderTable(parent, opts) })
          .on('error', $(parent).data('formhandler').failHandler)
      }
    })
  } catch (err) { if (err.message != 'Dropzone already attached.') throw err }
}

// move it inside filemanager
function renderTable(el, opts) {
  let filecol = _.find(opts.columns, c => c.name == 'file')
  filecol.link = filecol.link || el.dataset.src + DOWNLOAD_LINK
  $(el).on('load', function() {
    let btn = $(this).find('#uploadbtn').get(0)
    attach_dropzone(btn, el, el.dataset.src, true, renderTable.bind(this, el, opts))
    // Attach a dropzone to the whole element
    attach_dropzone(el, el, el.dataset.src, false, renderTable.bind(this, el, opts))
  }).formhandler(opts)
}

$.fn.filemanager = function(opts) {
  opts = opts || {columns: []}
  let newopts = Object.assign({}, opts, DEFAULT_OPTS)
  newopts.columns.forEach((s)=>{
    Object.assign(s, _.find(opts.columns, col => col.name == s.name))
  })
  newopts.columns.push(..._.filter(opts.columns, c => !(DEFAULT_COLS.includes(c.name))))
  this.each(function() {
    renderTable(this, newopts)
  })
}
