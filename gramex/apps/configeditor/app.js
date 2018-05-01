/* globals document, $, JSONEditor */
(function () {
  var script = document.currentScript,
      id = script.getAttribute('data-id') || 'editor',
      url = script.getAttribute('data-url') || 'config/',
      style = script.getAttribute('data-style') || ''
  document.write('<div id="' + id + '" style="' + style + '"></div>')
  document.addEventListener('DOMContentLoaded', function () {
    $.getJSON(url)
      .done(function(data) {
        _configeditor({spec: data, id: id})
      })
      .fail(function() {
        $.getJSON(url + 'init')
          .done(function(data) {
            _configeditor({spec: data, id: id})
          })
      })
  })
})()

function _configeditor(config) {
  // create the editor
  var container = document.getElementById(config.id)
  var options = {
    // TODO: Restrict editable fields
    onEditable: function(node) {
      switch (node.field) {
      case 'handler':
        return {field: false}
      default:
        return true
      }
    },
    // TODO: $schema via json-schema
    templates: [
      {
        text: 'FileHandler',
        title: 'Create a FileHandler',
        className: 'jsoneditor-type-object',
        field: 'Enter Key',
        value: {
          'pattern': 'Enter: URL pattern',
          'handler': 'FileHandler',
          'kwargs': {
            'path': '$YAMLPATH',
            'default_filename': 'README.md',
            'index': true
          }
        }
      },
      {
        text: 'FunctionHandler',
        title: 'Create a FunctionHandler',
        className: 'jsoneditor-type-object',
        field: 'Enter Key',
        value: {
          'pattern': 'Enter: URL pattern',
          'handler': 'FunctionHandler',
          'kwargs': {
            'function': 'Enter: Function',
            'headers': {
              'Content-Type': 'application/json'
            }
          }
        }
      }
    ]
  }
  var editor = new JSONEditor(container, options)
  editor.set(config.spec)
  container.editor = editor
  // var json = editor.get() // Get json
  return editor
}
