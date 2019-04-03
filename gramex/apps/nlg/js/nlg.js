/* globals currentEditIndex, grammarOptions, templates, args, df, currentEventHandlers, nlg_base */
/* exported addToNarrative, downloadConfig, setInitialConfig, uploadConfig, checkTemplate, saveTemplate, addCondition, addName, changeFHSetter, shareNarrative, copyToClipboard */
/* eslint-disable no-global-assign */
var narrative_name, dataset_name

class Template {
  constructor(
    text, tokenmap, inflections, fh_args, condition = '', setFHArgs = false, template = '',
    previewHTML = '', grmerr = null, name = ''
  ) {
    this.source_text = text
    // this.checkGrammar()
    this.tokenmap = tokenmap
    this.inflections = inflections
    for (let [token, tkobj] of Object.entries(tokenmap)) {
      if (Array.isArray(tkobj)) {
        this.tokenmap[token] = new Token(this, token, tkobj, this.inflections[token])
      }
      else {
        var newToken = new Token(this, token, tkobj.tokenlist, tkobj.inflections)
        newToken.template = tkobj.template
        this.tokenmap[token] = newToken
      }
    }
    this.fh_args = fh_args
    this.setFHArgs = setFHArgs
    this.condition = condition
    this.template = template
    this.previewHTML = previewHTML
    this.grmerr = grmerr
    this.name = name
  }

  checkGrammar() {
    let self = this
    $.ajax(
      {
        url: nlg_base + 'languagetool/?lang=en-us&q=' + encodeURIComponent(`${this.source_text}`),
        type: 'GET',
        success: function (e) {
          self.grmerr = e.matches
          self.highlight()
        },
      }
    )
  }

  makeTemplate() {
    var sent = this.source_text
    for (let [tk, tokenobj] of Object.entries(this.tokenmap)) {
      sent = sent.replace(tk, tokenobj.makeTemplate())
      if (tokenobj.varname) {
        var pattern = new RegExp(escapeRegExp(tokenobj.template))
        sent = sent.replace(pattern, t_templatize(tokenobj.varname))
        sent = `{% set ${tokenobj.varname} = ${tokenobj.makeTemplate()} %}\n\t` + sent
      }
    }
    if (this.condition) {
      sent = `{% if ${this.condition} %}\n\t` + sent + '\n{% end %}'
    }
    if (this.setFHArgs) {
      sent = addFHArgsSetter(sent, this.fh_args)
    }
    this.template = sent
    this.highlight()
    document.getElementById('edit-template').value = this.template
  }

  highlight() {
    var highlighted, span
    if (this.rendered_text != null) {
      highlighted = this.rendered_text
    } else { highlighted = this.source_text }
    for (let tk of Object.keys(this.tokenmap)) {
      highlighted = highlighted.replace(tk,
        `<span style="background-color:#c8f442">${tk}</span>`)
    }
    if (this.grmerr) {
      for (let i = 0; i < this.grmerr.length; i++) {
        var error = this.grmerr[i]
        if (this.rendered_text != null) {
          span = this.rendered_text.slice(error.offset, error.offset + error.length)
        } else {
          span = this.source_text.slice(error.offset, error.offset + error.length)
        }
        var popover_body = makeGrammarErrorPopover(span, error)
        highlighted = highlighted.replace(span, popover_body)
      }
    }
    this.previewHTML = highlighted
  }

  assignToVariable(token) {
    if (!(token.varname)) {
      var varname = prompt('Enter variable name:')
      if (varname) {
        token.varname = varname
      }
      this.makeTemplate()
    }
  }

  ignoreTokenTemplate(token) {
    token.is_ignored = true
    var enabled = token.enabledTemplate
    var escaped = escapeRegExp(enabled.tmpl)
    var expr = `\\{\\{\\ [^\\{\\}]*${escaped}[^\\{\\}]*\\ \\}\\}`
    var pattern = new RegExp(expr)
    this.template = this.template.replace(pattern, token.text)

    // UI
    document.getElementById('edit-template').value = this.template
    var btn = document.getElementById(`rmtoken-${currentEditIndex}-${token.text}`)
    btn.setAttribute('class', 'btn btn-success round')
    btn.setAttribute('title', 'Add Token')
    btn.innerHTML = '<i class="fa fa-plus-circle">'

    // change the listener to adder
    var parent = this
    btn.addEventListener('click', function () { parent.addTokenTemplate(token) })
  }

  addTokenTemplate(token) {
    token.is_ignored = false
    var enabled_tmpl = token.enabledTemplate
    var tmplstr = enabled_tmpl.tmpl
    if (token.inflections) {
      for (let i = 0; i < token.inflections.length; i++) {
        tmplstr = makeInflString(tmplstr, token.inflections[i])
      }
    }
    var pattern = new RegExp(token.text)
    this.template = this.template.replace(pattern, t_templatize(tmplstr))

    // UI
    document.getElementById('edit-template').value = this.template
    var btn = document.getElementById(`rmtoken-${currentEditIndex}-${token.text}`)
    btn.setAttribute('class', 'btn btn-danger round')
    btn.setAttribute('title', 'Ignore Token')
    btn.innerHTML = '<i class="fa fa-times-circle">'

    // change the listener to remover
    var parent = this
    btn.addEventListener('click', function () { parent.ignoreTokenTemplate(token) })
  }

  get condition() {
    return this._condition
  }

  set condition(condt) {
    this._condition = condt
  }

  get fh_args() {
    return this._fh_args
  }

  set fh_args(fh_args) {
    this._fh_args = fh_args
  }

  makeSettingsTable() {
    // make the HTML table for the nth template.
    var html = ''
    for (let [token, tkobj] of Object.entries(this.tokenmap)) {
      html += `<tr><th scope="row" class="align-middle">${token}</th>`

      if (tkobj.tokenlist.length > 1) {
        var dd_html = tkobj.makeSearchResultsDropdown()
        html += `<td>${dd_html}</td>`
      } else {
        html += `<td class="align-middle" style="font-family:monospace">${tkobj.tokenlist[0].tmpl}</td>`
      }

      // grammar dropdown
      var grop_html = tkobj.makeGrammarOptionsSelector(currentEditIndex)
      html += `<td class="align-middle">${grop_html}</td>`

      // add button to assign to variable
      html += `<td class="align-middle">
                <button id="assignvar-${currentEditIndex}-${token}" title="Assign to variable" class="btn btn-success round">
                <i class="fa fa-plus-circle">
            </td>`

      // remover dropdown
      html += `<td class="align-middle">
                    <button id="rmtoken-${currentEditIndex}-${token}" title="Ignore token" class="btn btn-danger round">
                        <i class="fa fa-times-circle">
                    </button></td></tr>`
    }
    document.getElementById('table-body').innerHTML = html

    for (let [token, tkobj] of Object.entries(this.tokenmap)) {
      // add search result dropdown listeners
      if (tkobj.tokenlist.length > 1) {
        let dd_id = `srdd-${currentEditIndex}-${token}`
        document.getElementById(dd_id).onchange = function () { tkobj.changeTokenTemplate() }
      }

      // add grammar options listeners
      var gramOptSelect = document.getElementById(`gramopt-select-${currentEditIndex}-${token}`)
      gramOptSelect.addEventListener('change', function () { tkobj.changeGrammarOption() })

      // add variable assignment listener
      var assignBtn = document.getElementById(`assignvar-${currentEditIndex}-${token}`)
      var parent = this
      assignBtn.addEventListener('click', function () { parent.assignToVariable(tkobj) })

      // Add remove listener
      var rmtokenbtn = document.getElementById(`rmtoken-${currentEditIndex}-${token}`)
      rmtokenbtn.addEventListener('click', function () { parent.ignoreTokenTemplate(tkobj) })
    }

  }
}

function makeGrammarErrorPopover(span, errobj) {
  var errmsg = errobj.message.replace(/"/g, '\'')
  return `<span style="background-color:#ed7171" data-toggle="popover" data-trigger="hover"
    title="${errmsg}"
    data-placement="top">${span}</span>`
}

class Token {
  constructor(parent, text, tokenlist, inflections, varname = null, template = '') {
    this.parent = parent
    this.text = text
    this.tokenlist = tokenlist
    this.inflections = inflections
    this.varname = varname
    this.template = template
    this.is_ignored = false
  }

  toJSON() {
    return {
      text: this.text, tokenlist: this.tokenlist, inflections: this.inflections,
      varname: this.varname, template: this.template
    }
  }

  get varname() {
    return this._varname
  }

  set varname(value) {
    this._varname = value
    if (value) {
      this.template = this._varname
    }
  }

  makeTemplate() {
    if (this.is_ignored) { return this.text }
    var enabled = this.enabledTemplate
    var tmplstr = enabled.tmpl
    if (this.inflections) {
      for (let i = 0; i < this.inflections.length; i++) {
        tmplstr = makeInflString(tmplstr, this.inflections[i])
      }
    }
    if (this.varname) {
      this.template = tmplstr
    } else { this.template = t_templatize(tmplstr) }
    return this.template
  }

  get enabledTemplate() {
    for (let i = 0; i < this.tokenlist.length; i++) {
      if (this.tokenlist[i].enabled) {
        return this.tokenlist[i]
      }
    }
    return undefined
  }

  makeSearchResultsDropdown() {
    var dropdown_id = `srdd-${currentEditIndex}-${this.text}`
    var html = `
            <div style="font-family:monospace">
            <select class="selectpicker" id="${dropdown_id}">
            <option selected>
                ${this.enabledTemplate.tmpl}
            </option>`
    for (let i = 0; i < this.tokenlist.length; i++) {
      let tmpl = this.tokenlist[i]
      if (!(tmpl.enabled)) {
        html += `<div style="font-family:monospace">
                            <option>${tmpl.tmpl}</option>
                        </div>`
      }
    }
    // add dd option change listeners here.
    return html + '</select></div>'
  }

  findAppliedInflections() {
    var applied_inflections = new Set()
    if (this.inflections) {
      for (let i = 0; i < this.inflections.length; i++) {
        applied_inflections.add(this.inflections[i].fe_name)
      }
    }
    return applied_inflections
  }

  makeGrammarOptionsSelector(editIndex) {
    var html = `<select id="gramopt-select-${editIndex}-${this.text}" class="select-multiple" multiple="multiple">`
    var appliedInfls = this.findAppliedInflections()
    var selected
    for (let fe_name of Object.keys(grammarOptions)) {
      // check if this inflection is already applied
      if (appliedInfls.has(fe_name)) {
        selected = 'selected'
      }
      else { selected = '' }
      html += `<option ${selected}>${fe_name}</option>`
    }
    return html + '</select>'
  }

  changeGrammarOption() {
    // remove all currently applied inflections on the token
    this.inflections = []

    // add the currently selected inflections
    var selected = document.getElementById(`gramopt-select-${currentEditIndex}-${this.text}`).selectedOptions
    var inflections = Array.from(selected).map(x => x.value)
    var newInflections = []
    for (let i = 0; i < inflections.length; i++) {
      let infl = {}
      let fe_name = inflections[i]
      infl['fe_name'] = fe_name
      infl['source'] = grammarOptions[fe_name]['source']
      infl['func_name'] = grammarOptions[fe_name]['func_name']
      newInflections.push(infl)
    }
    this.inflections = newInflections
    this.parent.makeTemplate()
  }

  changeTokenTemplate() {
    var dd_id = `srdd-${currentEditIndex}-${this.text}`
    var newTmpl = document.getElementById(dd_id).value
    for (let i = 0; i < this.tokenlist.length; i++) {
      var tmplobj = this.tokenlist[i]
      if (tmplobj.tmpl == newTmpl) {
        tmplobj.enabled = true
      }
      else { tmplobj.enabled = false }
    }
    this.parent.makeTemplate()
  }
}


function addToNarrative() {
  // pick text from the "Type something" box, templatize, and add to narrative
  $.ajax({
    type: 'POST',
    url: nlg_base + 'textproc',
    data: {
      'args': JSON.stringify(args), 'data': JSON.stringify(df),
      'text': JSON.stringify([document.getElementById('textbox').value])
    },
    success: addToTemplates
  })
}

function addToTemplates(payload) {
  payload = payload[0]
  var template = new Template(
    payload.text, payload.tokenmap, payload.inflections, payload.fh_args)
  template.setFHArgs = payload.setFHArgs
  // template.grmerr = payload.grmerr
  // checkGrammar(template)
  template.makeTemplate()
  templates.push(template)
  renderPreview(null)
}

function renderPreview(fh) {
  if (fh) {
    df = fh.formdata
    args = g1.url.parse(g1.url.parse(window.location.href).hash).searchList
    refreshTemplates()
    return true
  }
  var innerHTML = '<p>\n'
  for (var i = 0; i < templates.length; i++) {
    innerHTML += '<div class="pb-1">' + getRmButton(i) // + getConditionBtn(i) + getEditTemplateBtn(i)
      + getSettingsBtn(i) + '\t' + templates[i].previewHTML + '</div>'
  }
  innerHTML += '</p>'
  document.getElementById('template-preview').innerHTML = innerHTML

  // add listeners to buttons
  for (let i = 0; i < templates.length; i++) {

    // add the remove listener
    var btn = document.getElementById(`rm-btn-${i}`)
    var deleteListener = function () { deleteTemplate(i) }
    btn.addEventListener('click', deleteListener)

    // add setting listener
    btn = document.getElementById(`settings-btn-${i}`)
    var settingsListener = function () { triggerTemplateSettings(i) }
    btn.addEventListener('click', settingsListener)
  }
}

function refreshTemplates() {
  var tmpls = templates.map(x => x.template)
  $.ajax({
    type: 'POST',
    url: nlg_base + 'render-template',
    data: {
      'args': JSON.stringify(args), 'data': JSON.stringify(df),
      'template': JSON.stringify(tmpls)
    },
    success: updateTemplates
  })
}

function updateTemplates(payload) {
  for (let i = 0; i < payload.length; i++) {
    var tmpl = templates[i]
    tmpl.rendered_text = payload[i].text
    tmpl.grmerr = payload[i].grmerr
    tmpl.highlight()
  }
  renderPreview(null)
}

function deleteTemplate(n) {
  // Delete a template
  templates.splice(n, 1)
  delete currentEventHandlers[`condt-btn-${n}`]
  renderPreview(null)
}

function triggerTemplateSettings(sentid) {
  currentEditIndex = sentid
  editTemplate(currentEditIndex)
  $('#template-settings').modal({ 'show': true })
  $('#condition-editor').focus()
  // $(function() { $('.select-multiple').select2() })
}

function editTemplate(n) {
  currentEditIndex = n
  document.getElementById('edit-template').value = templates[n].template
  document.getElementById('tmpl-setting-preview').innerHTML = templates[n].previewHTML
  var currentCondition = templates[n].condition
  if (currentCondition) {
    document.getElementById('condition-editor').value = currentCondition
  }
  else {
    document.getElementById('condition-editor').value = ''
  }
  if (templates[n].name != null) {
    document.getElementById('tmpl-name-editor').value = templates[n].name
  }
  else {
    document.getElementById('tmpl-name-editor').value = ''
  }
  templates[n].makeSettingsTable()
}


function saveConfig() {
  var elem = document.getElementById('narrative-name-editor')
  if (!(elem.value)) {
    alert('Please name the narrative.')
    elem.focus()
  } else {
    narrative_name = elem.value
    $.ajax({
      url: nlg_base + 'save-config',
      type: 'POST',
      data: { config: JSON.stringify(templates), name: narrative_name, dataset: dataset_name },
      headers: { 'X-CSRFToken': false },
      success: function () { $('.alert-success').show() }
    })
  }
}

function downloadConfig() {
  let url = nlg_base + 'config-download?config=' + encodeURIComponent(JSON.stringify(templates))
    + '&name=' + encodeURIComponent(document.getElementById('narrative-name-editor').value)
  if (document.getElementById('download-data-cb').checked) {
    url = url + '&data=' + encodeURIComponent(JSON.stringify(df))
  }
  $.ajax({
    url: url,
    responseType: 'blob',
    type: 'GET',
    headers: { 'X-CSRFToken': false },
    success: function () { window.location = url }
  })
}

function setInitialConfig() {
  $.ajax({
    // url: 'initconf/meta.json',
    url: nlg_base + 'initconf',
    type: 'GET',
    success: function (e) {
      dataset_name = e.dsid
      narrative_name = e.nrid
      if (e.config) { setConfig(e.config) }
    },
    error: function () { return false }
  })
  // $.ajax({
  //     url: 'initconf/config.json',
  //     type: 'GET',
  //     success: setConfig,
  //     error: function (e) { return false }
  // })
}

function setConfig(configobj) {
  templates = []
  for (let i = 0; i < configobj.config.length; i++) {
    var tmpl = configobj.config[i]
    var tmplobj = new Template(
      tmpl.text, tmpl.tokenmap, tmpl.inflections,
      tmpl._fh_args, tmpl._condition, tmpl.setFHArgs,
      tmpl.template, tmpl.previewHTML, tmpl.grmerr, tmpl.name)
    templates.push(tmplobj)
  }
  document.getElementById('narrative-name-editor').value = configobj.name
  args = null
  renderPreview(null)
}

function uploadConfig() {
  var reader = new FileReader()
  reader.onload = function () {
    var config = JSON.parse(reader.result)
    templates = []
    for (let i = 0; i < config.config.length; i++) {
      var tmpl = config.config[i]
      var tmplobj = new Template(
        tmpl.text, tmpl.tokenmap, tmpl.inflections,
        tmpl._fh_args, tmpl._condition, tmpl.setFHArgs,
        tmpl.template, tmpl.previewHTML, tmpl.grmerr, tmpl.name)
      templates.push(tmplobj)
    }
    document.getElementById('narrative-name-editor').value = config.name
    args = null
    renderPreview(null)
  }
  var elem = document.getElementById('config-upload')
  reader.readAsText(elem.files[0])
}

function checkTemplate() {
  // Render the template found in the template editor box against the df and args.
  renderTemplate([document.getElementById('edit-template').value], editAreaCallback, showTraceback)
}

function showTraceback(payload) {
  let traceback = $($.parseHTML(payload.responseText)).filter('#traceback')[0]
  document.getElementById('traceback').innerHTML = traceback.innerHTML
  $('#tb-modal').modal({ 'show': true })
}

function renderTemplate(text, success, error) {
  // render an arbitrary template and do `success` on success.
  $.ajax({
    type: 'POST',
    url: nlg_base + 'render-template',
    data: {
      'args': JSON.stringify(args), 'data': JSON.stringify(df),
      'template': JSON.stringify(text)
    },
    success: success,
    error: error
  })
}

function editAreaCallback(payload) {
  var template = templates[currentEditIndex]
  template.rendered_text = payload[0].text
  template.highlight()
  document.getElementById('tmpl-setting-preview').innerHTML = template.previewHTML
}

function saveTemplate() {
  // Save the template found in the template editor box at `currentEditIndex`.
  var tbox = document.getElementById('edit-template')
  var pbox = document.getElementById('tmpl-setting-preview')
  templates[currentEditIndex].template = tbox.value
  templates[currentEditIndex].text = pbox.textContent
  templates[currentEditIndex].highlight()
  renderPreview(null)
  document.getElementById('save-template').disabled = true
}

function addCondition() {
  var condition = document.getElementById('condition-editor').value
  if (condition) {
    var template = templates[currentEditIndex]
    template.condition = condition
    template.makeTemplate()
    document.getElementById('edit-template').value = template.template
  }

}

function addName() {
  var name = document.getElementById('tmpl-name-editor').value
  if (name) {
    templates[currentEditIndex].name = name
  }
}

function changeFHSetter() {
  let template = templates[currentEditIndex]
  template.setFHArgs = document.getElementById('fh-arg-setter').checked
  template.makeTemplate()
  document.getElementById('edit-template').value = template.template
}

function t_templatize(x) { return '{{ ' + x + ' }}' }

function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')  // $& means the whole matched string
}

function makeInflString(tmpl, infl) {
  var tmplstr = tmpl
  var infl_source = infl.source
  if (infl_source == 'str') {
    tmplstr = tmplstr + `.${infl.func_name}()`
  }
  else { tmplstr = `${infl.source}.${infl.func_name}(${tmplstr})` }
  return tmplstr
}

function addFHArgsSetter(sent, fh_args) {
  var setterLine = `{% set fh_args = ${JSON.stringify(fh_args)} %}\n`
  setterLine += '{% set df = U.grmfilter(orgdf, fh_args.copy()) %}\n'
  return setterLine + sent
}

function getEditorURL() {
  let url = g1.url.parse(window.location.href)
  return `${url.protocol}://${url.origin}${url.directory}nlg/edit-narrative?dsid=${dataset_name}&nrid=${narrative_name}`
}

function getNarrativeEmbedCode() {
  let url = g1.url.parse(window.location.href)
  url = url + 'render-live-template'
  let html = `
    <div id="narrative-result"></div>
    <script>
        $('.formhandler').on('load',
            function (e) {
                $.ajax({
                    url: "${url}",
                    type: "POST",
                    data: {
                        data: JSON.stringify(e.formdata),
                        nrid: "${narrative_name}",
                        style: true
                    },
                    success: function (pl) {
                        document.getElementById("narrative-result").innerHTML = pl
                    }
                })
            }
        )
    </script>
    `
  return html
}

function shareNarrative() {
  saveConfig()
  var editor_url = document.getElementById('share-editor-url')
  editor_url.value = getEditorURL()
  var embed_code = document.getElementById('share-narrative-url')
  embed_code.innerText = getNarrativeEmbedCode()
  $('#share-modal').modal({ 'show': true })
}

function copyToClipboard(elem_id) {
  var elem = document.getElementById(elem_id)
  elem.select()
  document.execCommand('copy')

}

// Markup buttons
function getRmButton(n) {
  // Get HTML for the delete template button.
  return `
    <button id="rm-btn-${n}" title="Remove" type="button" class="btn btn-danger btn-sm">
        <i class="fa fa-trash"></i>
    </button>
    `
}

function getSettingsBtn(n) {
  return `
    <button id="settings-btn-${n}" title="Settings" type="button" class="btn btn-primary btn-sm">
        <i class="fa fa-wrench"></i>
    </button>
    `
}
