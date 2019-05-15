$('script.outputfinal').template({ data: { 'url': 'index5.html', 'text': 'Our Final Output Should Look Like This' } })
$('script.output4').template({ data: { url: 'index4.html', 'text': 'Our current Output Should Look Like This' } })
$('script.action-demo').template({ data: { 'card_body_text': 'Action Items, Points of interest, or Code Snippets will be displayed in a card similar to this one.' } })
$('script.action-save').template({ data: { 'card_body_text': 'Create a folder at a convenient location on your computer and move the downloaded dataset file into it.' } })
$('script.step0coa').template({ data: { 'card_body_text': "<ul><li>To set up the project, create a file named <kbd>gramex.yaml</kbd> in the project folder, leave it blank for now.</li><li>Create a second file called <kbd>index.html</kbd> and put any html you like in there. For now, just a simple bit of text will do.</li>" } })
$.get('snippets/hello.sh').done((e) => {
  $('script.step0term').template({
    data: {
      card_body_text: 'Open up a terminal, navigate to the project folder and type the following:',
      code: true,
      card_body_code_type: 'bash',
      card_body_code: e,
      filename: 'Terminal'
    }
  })
})
$('script.step0term2').template({
  data: {
    card_body_text: 'Type the following command to start the Gramex server.',
    card_body_type: 'bash',
    code: true,
    card_body_code: 'gramex',
    filename: 'Terminal'
  }
})
$('script.step0output').template({ data: { url: 'index2.html', text: 'Current Output' } })
$.get('snippets/gramex1.yaml').done((e) => {
  $('script.step1gramex').template({
    data: {
      card_body_text: 'Create a formhandler endpoint on our server by adding the following lines to the empty <kbd>gramex.yaml</kbd> file, which we had created in the previous section:',
      card_body_type: 'lang-yaml',
      code: true,
      card_body_code: e,
      filename: 'gramex.yaml'
    }
  })
})
$('script.step1dataop').template({ data: { url: 'data?_limit=10', text: 'JSON Payload' } })

$('script.step1dataophtml').template({ data: { url: 'data?_limit=10&_format=html', text: 'JSON Payload as HTML Table' } })
$.get('snippets/index1.html').done((e) => {
  $('script.step2coa').template({
    data:
    {
      card_body_text: "At the moment, our <kbd>index.html</kbd> file just has some text in it. Let's add the following HTML to it.",
      code: true,
      card_body_code: e,
      filename: 'index.html',
      card_body_type: 'lang-html'
    }
  })
})
$.get('snippets/gramex_2.yaml').done((e) => {
  $('script.step2coa2').template({
    data: {
      card_body_text: 'To use these in our dashboard, we add the following lines to our <kbd>gramex.yaml</kbd>:',
      code: true,
      filename: 'gramex.yaml',
      card_body_type: 'lang-yaml',
      card_body_code: e
    }
  })
})
$.get('gramex2.yaml').done((e) => {
  $('script.step2coa3').template({
    data: {
      card_body_text: 'The final <kbd>gramex.yaml</kbd> looks like',
      code: true,
      filename: 'gramex.yaml',
      card_body_type: 'lang-yaml',
      card_body_code: e
    }
  })
})
$('script.step2output').template({ data: { url: 'index6.html', text: 'Current Output' } })
$.get('snippets/fh.html').done((e) => {
  $('script.step3coa').template({
    data: {
      code: true,
      card_body_text: 'To show the data as a table, insert the following lines in <kbd>index.html</kbd>:',
      filename: 'index.html',
      'card_body_type': 'lang-html',
      card_body_code: e
    }
  })
})
$.get('snippets/fh-after.html').done((e) => {
  $('script.step3html').template({
    data: {
      card_body_text: 'Our current <kbd>index.html<\kbd> looks like:',
      code: true,
      card_body_code_type: 'lang-html',
      card_body_code: e,
      filename: 'index.html'
    }
  })
})
$('script.step3output').template({ data: { url: 'index7.html', text: 'Our Current Ouput' } })
$.get('snippets/chartspec.html').done((e) => {
  $('script.step4coa1').template({
    data: {
      card_body_text: 'Add the following <span class="font-italic">chart specification</span> to your HTML:',
      card_body_code_type: 'lang-html',
      code: true,
      filename: 'index.html',
      card_body_code: e
    }
  })
})
$.get('snippets/vega1.html').done((e) => {
  $('script.step4coa2').template({
    data: {
      card_body_text: 'Add a div in the page in which to place the chart, and a little bit of Javascript code to render the chart:',
      card_body_code_type: 'lang-html',
      code: true,
      filename: 'index.html',
      card_body_code: e
    }
  })
})
$.get('index4.html').done((e) => {
  $('script.step4coa3').template({
    data: {
      card_body_text: 'At this stage, our current <kbd>index.html<\kbd> looks like:',
      code: true,
      card_body_code_type: 'lang-html',
      card_body_code: e,
      filename: 'index.html'
    }
  })
})

$.get('snippets/render.js').done((e) => {
  $('script.step5coa1').template({
    data: {
      card_body_text: 'Create a function which accepts the fields to be updated, the <code>&lt;div&gt;</code> to place the chart, the X-axis label and the title of the chart.',
      code: true,
      filename: 'index.html',
      card_body_code: e,
      card_body_code_type: 'lang-javascript'
    }
  })
})
