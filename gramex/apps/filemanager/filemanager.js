function get_default_opts(url) {
  return {
    edit: true,
    columns: [
      {
        name: "file", link: `${url}?id=<%- row.id %>&_format=file&_download`,
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
      {name: "tags"},
    ]
  }
}

function updateColumns(fm, fh) {
  // Update the filemanager columns with whatever the user has provided
  // under the formhandler columns, but keep some reserved as default.
  let default_columns = _.map(fm, "name")
  let user_columns = _.map(fh, "name")
  let to_add = _.difference(user_columns, default_columns)
  let cols_to_add = _.filter(fh, function(d) {return to_add.includes(d.name)})
  fm.push(...cols_to_add)
  return fm

}

function renderTable(el, opts) {
  let url = el.dataset.src
  let default_opts = get_default_opts(url)
  let user_columns = (opts.columns || []).slice()
  Object.assign(opts, default_opts)
  opts.columns = updateColumns(default_opts.columns, user_columns)
  $(el).on('load', function(e) {
    let btn = $(this).find('[id^="formhandler-export-"]').get(0)
    $(btn).text('Upload')
    $(btn).removeClass('dropdown-toggle')
    $(btn).removeClass('btn-light')
    $(btn).addClass('btn-primary')
    if (!($(btn).hasClass('dz-clickable'))) {
      $(btn).dropzone({
        url: $(el).attr('data-src'),
        createImageThumbnails: false,
        previewTemplate: "<div></div>",
        init: function() {
          this.on('success', function(e) { renderTable(el, opts) })
        }
      })
    }
    $(btn).next().remove()
    // Attach a dropzone to the whole element
    if (!(el.dropzone)) {
      $(el).dropzone({
        url: $(el).attr('data-src'),
        clickable: false,
        createImageThumbnails: false,
        previewTemplate: "<div></div>",
        init: function() {
          this.on('success', function(e) { renderTable(el, opts) })
        }
      })
    }
  })
  .formhandler(opts)
}

$.fn.filemanager = function(opts) {
  // update opts with filemanager's default opts
  opts = opts || {}
  this.each(function() {
    let el = this
    renderTable(el, opts)
  })
}
