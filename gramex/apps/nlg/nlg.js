/* globals currentEditIndex, grammarOptions, templates, args, df, currentEventHandlers, nlg_base */
/* exported addToNarrative, setInitialConfig, checkTemplate, saveTemplate, addCondition, addName, changeFHSetter, shareNarrative, copyToClipboard */
/* eslint-disable no-global-assign */
var narrative_name, dataset_name

class Template {
  constructor(
    text, tokenmap, inflections, fh_args, condition = '', setFHArgs = false, template = '',
    previewHTML = '', grmerr = null, name = ''
  ) {
    this.source_text = text
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
    $.getJSON(
        nlg_base + '/languagetool/?lang=en-us&q=' + encodeURIComponent(`${this.source_text}`)
    ).done((e) => {
        self.grmerr = e.matches
        self.highlight()
    })
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
    $('#edit-template').val(this.template)
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
      let varname = prompt('Enter variable name:')
      if (varname) {
        token.varname = varname
      }
      this.makeTemplate()
    }
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
    $('#tmplsettings').template({tokenmap: this.tokenmap, grammarOptions: grammarOptions})

    for (let [token, tkobj] of Object.entries(this.tokenmap)) {
      // add search result dropdown listeners
      let tkselector = token.replace(/\s/g, "_")
      if (tkobj.tokenlist.length > 1) {
        $(`#srdd-${currentEditIndex}-${tkselector}`).on('change', function () { tkobj.changeTokenTemplate() })
      }

      // add grammar options listeners
      $(`#gramopt-select-${currentEditIndex}-${tkselector}`).on('change', (e) => { tkobj.changeGrammarOption() })

      // add variable assignment listener
      var parent = this
      $(`#assignvar-${currentEditIndex}-${tkselector}`).on('click', (e) => { parent.assignToVariable(tkobj) })

      // remove listener
      $(`#assignvar-${currentEditIndex}-${tkselector}`).on('click', (e) => { parent.ignoreTokenTemplate(tkobj) })
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
  constructor(parent, text, tokenlist, inflections, template = '') {
    this.parent = parent
    this.text = text
    this.tokenlist = tokenlist
    this.inflections = inflections
    this.template = template
  }

  toJSON() {
    return {
      text: this.text, tokenlist: this.tokenlist, inflections: this.inflections,
      template: this.template
    }
  }

  makeTemplate() {
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

  changeGrammarOption() {
    // remove all currently applied inflections on the token
    this.inflections = []

    // add the currently selected inflections
    var inflections = $(`#gramopt-select-${currentEditIndex}-${this.text.replace(/\s/g, '_')}`).val()
    var newInflections = []
    for (let i = 0; i < inflections.length; i++) {
      let infl = {}
      let fe_name = inflections[i]
      infl['fe_name'] = inflections[i]
      infl['source'] = grammarOptions[fe_name]['source']
      infl['func_name'] = grammarOptions[fe_name]['func_name']
      newInflections.push(infl)
    }
    this.inflections = newInflections
    this.parent.makeTemplate()
  }

  changeTokenTemplate() {
    var newTmpl = $(`#srdd-${currentEditIndex}-${this.text.replace(/\s/g, '_')}`).val()
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
  $.post(
    nlg_base + '/textproc',
    JSON.stringify({
      'args': args, 'data': df,
      'text': [$('#textbox').val()]
    }), addToTemplates
  )
}

function addToTemplates(payload) {
  payload = payload[0]
  var template = new Template(
    payload.text, payload.tokenmap, payload.inflections, payload.fh_args)
  template.setFHArgs = payload.setFHArgs
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
  $('#template-preview').template({templates: templates})
  for (let i = 0; i < templates.length; i++) {
    // add the remove listener
    var deleteListener = function () { deleteTemplate(i) }
    $(`#rm-btn-${i}`).on('click', deleteListener)

    // add setting listener
    var settingsListener = function () { triggerTemplateSettings(i) }
    $(`#settings-btn-${i}`).on('click', settingsListener)
  }
}

function refreshTemplates() {
  $.post(nlg_base + '/render-template',
    JSON.stringify({
      'args': args, 'data': df,
      'template': templates.map(x => x.template)
    }), updateTemplates
  )
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
}

function editTemplate(n) {
  currentEditIndex = n
  $('#edit-template').val(templates[n].template)
  $('#tmpl-setting-preview').html( templates[n].previewHTML)
  $('#condition-editor').val(templates[n].condition)
  $('#tmpl-name-editor').val(templates[n].name)
  templates[n].makeSettingsTable()
}


function saveConfig() {
  var elem = $('#narrative-name-editor')
  if (!(elem.val())) {
    alert('Please name the narrative.')
    elem.focus()
    return false
  } else {
    narrative_name = elem.val()
    $.ajax({
      url: nlg_base + '/save-config',
      type: 'POST',
      data: { config: JSON.stringify(templates), name: narrative_name, dataset: dataset_name },
      headers: { 'X-CSRFToken': false },
      success: function () { $('.alert-success').show() },
      error: function(httpObj) {
        if (httpObj.status == 401) {
          alert('Please login to save the narrative.')
        }
      }
    })
  }
  return true
}

function setInitialConfig() {
  $.getJSON(nlg_base + '/initconf',
    (e) => {
      dataset_name = e.dsid
      narrative_name = e.nrid
      if (e.config) { setConfig(e.config) }
    },
  )
}

function setConfig(configobj) {
  templates = []
  for (let i = 0; i < configobj.config.length; i++) {
    var tmpl = configobj.config[i]
    var tmplobj = new Template(
      tmpl.source_text, tmpl.tokenmap, tmpl.inflections,
      tmpl._fh_args, tmpl._condition, tmpl.setFHArgs,
      tmpl.template, tmpl.previewHTML, tmpl.grmerr, tmpl.name)
    templates.push(tmplobj)
  }
  $('#narrative-name-editor').val(configobj.name)
  args = null
  renderPreview(null)
}

function checkTemplate() {
  // Render the template found in the template editor box against the df and args.
  $.post(nlg_base + '/render-template',
    JSON.stringify({
      'args': args, 'data': df,
      'template': [$('#edit-template').val()]
    })
  ).done(editAreaCallback).fail(showTraceback)
}

function showTraceback(payload) {
  let traceback = $($.parseHTML(payload.responseText)).filter('#traceback')[0]
  $('#traceback').html(traceback.innerHTML)
  $('#tb-modal').modal({ 'show': true })
}


function editAreaCallback(payload) {
  var template = templates[currentEditIndex]
  template.rendered_text = payload[0].text
  template.highlight()
  $('#tmpl-setting-preview').html(template.previewHTML)
}

function saveTemplate() {
  // Save the template found in the template editor box at `currentEditIndex`.
  templates[currentEditIndex].template = $('#edit-template').val()
  templates[currentEditIndex].text = $('#tmpl-setting-preview').text()
  templates[currentEditIndex].highlight()
  $('#save-template').attr('disabled', true)
  renderPreview(null)
}

function addCondition() {
  var condition = $('#condition-editor').val()
  if (condition) {
    var template = templates[currentEditIndex]
    template.condition = condition
    template.makeTemplate()
    $('#edit-template').val(template.template)
  }

}

function addName() {
  let name = $('#tmpl-name-editor').val()
  if (name) {
    templates[currentEditIndex].name = name
  }
}

function changeFHSetter() {
  let template = templates[currentEditIndex]
  template.setFHArgs = $('#fh-arg-setter').attr('checked')
  template.makeTemplate()
  $('#edit-template').val(template.template)
}

/* eslint-disable no-unused-vars */
function t_templatize(x) { return '{{ ' + x + ' }}' }
/* eslint-enable no-unused-vars */

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
  let setterLine = `{% set fh_args = ${JSON.stringify(fh_args)} %}\n`
  setterLine += '{% set df = U.grmfilter(orgdf, fh_args.copy()) %}\n'
  return setterLine + sent
}


function getNarrativeEmbedCode() {
  let nlg_path = g1.url.parse(window.location.href).pathname
  let html = `
    <div id="narrative-result"></div>
    <script>
      $('.formhandler').on('load',
        (e) => {
          $.post("${nlg_path}/render-live-template",
            {
              data: JSON.stringify(e.formdata),
              nrid: "${narrative_name}", style: true
            }, (f) => $("#narrative-result").html(pl)
          )
        }
      )
    </script>
    `
  return html
}

function shareNarrative() {
  if (saveConfig()) {
    $('#share-narrative-url').text(getNarrativeEmbedCode())
    $('#share-modal').modal({ 'show': true })
  }
}

function copyToClipboard(elem_id){
  var $temp = $("<div>");
  $("body").append($temp);
  $temp.attr("contenteditable", true)
       .html($('#' + elem_id).html()).select()
       .on("focus", function() { document.execCommand('selectAll',false,null) })
       .focus();
  document.execCommand("copy");
  $temp.remove();
}

function findAppliedInflections(tkobj) {
  var applied_inflections = new Set()
  if (tkobj.inflections) {
    for (let i = 0; i < tkobj.inflections.length; i++) {
      applied_inflections.add(tkobj.inflections[i].fe_name)
    }
  }
  return applied_inflections
}
