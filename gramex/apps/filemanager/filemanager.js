const DOWNLOAD_LINK = '?id=<%- row.id %>&_format=file&_download'
const DEFAULT_OPTS = {
  edit: true,
  columns: [
    {
      name: "file", // link: `${url}`,
      editable: {
        input: "text"
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
    {name: "tags", editable: {input: "text"}},
  ],
  exportTemplate: '<button id="uploadbtn" class="btn btn-primary">Upload</button>',
  notification: ".drivenotif"
}
const NOTIFICATION_TEMPLATE = `
<div class="alert alert-warning alert-dismissible" role="alert">
  <template class="notif"><%= message %></template>
  <button type="button" class="close" data-dismiss="alert" aria-label="Close">
    <span aria-hidden="true">&times;</span>
  </button>
</div>`
const DEFAULT_COLS = _.map(DEFAULT_OPTS.columns, "name")

function attach_dropzone(el, opts, parent = null, clickable = true) {
  if (!(parent)) { parent = el }
  $(el).dropzone({
    url: $(parent).attr('data-src'),
    clickable: clickable,
    createImageThumbnails: false,
    previewTemplate: "<div></div>",
    init: function() {
      this.on('success', function(e) { renderTable(parent, opts) })
      .on('error', function(file, error, xhr) {
        $(opts.notification).html(NOTIFICATION_TEMPLATE)
        if (xhr.status == 413) {
          $("template.notif").template({message: 'File too large.'})
        } else if (xhr.status == 415) {
          $("template.notif").template({message: 'File type not allowed.'})
        } else if (xhr.status == 0) {
          $("template.notif").template({message: 'Server not reachable.'})
        }
      })
    }
  })
}

function renderTable(el, opts) {
  let filecol = _.find(opts.columns, (c) => {return c.name == "file"})
  filecol.link = filecol.link || el.dataset.src + DOWNLOAD_LINK
  $(el).on('load', function(e) {
    let btn = $(this).find('#uploadbtn').get(0)
    if (!($(btn).hasClass('dz-clickable'))) {
      attach_dropzone(btn, opts, el)
    }
    // Attach a dropzone to the whole element
    if (!(el.dropzone)) {
      attach_dropzone(el, opts, clickable = false)
    }
  })
  .formhandler(opts)
}

$.fn.filemanager = function(opts) {
  opts = opts || {columns: []}
  newopts = Object.assign({}, opts, DEFAULT_OPTS)
  newopts.columns.forEach((s)=>{
    Object.assign(s, _.find(opts.columns, (col) => {return col.name == s.name}))
  })
  newopts.columns.push(..._.filter(opts.columns, (c) => {return !(DEFAULT_COLS.includes(c.name))}))
  this.each(function() {
    renderTable(this, newopts)
  })
}
