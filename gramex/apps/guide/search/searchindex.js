// Creates searchindex.json as a lunr index
// Usage: node searchindex.js
var fs = require('fs')
var path = require('path')
var lunr = require('lunr')
var glob = require('glob')
var marked = require('marked')
var fm = require('front-matter')
var root = path.join(__dirname, '..')

var index = []
var docs = []
glob('*/*.md', { cwd: root }, function (err, files) {
  files.forEach(function (file) {
    var text = fs.readFileSync(path.join(root, file), 'utf8')
    var content = fm(text)
    var tokens = marked.lexer(content.body)
    var title = content.attributes.title
    var prefix = content.attributes.prefix || title
    var body = []
    tokens.forEach(function (token) {
      if (token.type == 'heading') {
        add_doc(title, prefix, body, file)
        title = token.text
        body = []
      } else if (token.text) {
        body.push(token.text)
      }
    })
    if (title)
      add_doc(title, prefix, body, file)
  })
  var idx = lunr(function () {
    this.field('title')
    this.field('body')
    this.field('id')
    var lunr_index = this
    index.forEach(function (entry) {
      lunr_index.add(entry)
    })
  })
  fs.writeFileSync(path.join(__dirname, 'searchindex.json'), JSON.stringify({
    'docs': docs,
    'index': idx.toJSON()
  }))
})

function url(file, title) {
  var slug = title.toLowerCase().replace(/[^\w]+/g, '-')
  return file.replace(/README.md/, '') + '#' + slug
}

function add_doc(title, prefix, body, file) {
  index.push({ title: title, body: body.join(' '), id: docs.length })
  docs.push({ title: title, prefix: prefix, link: url(file, title) })
}
