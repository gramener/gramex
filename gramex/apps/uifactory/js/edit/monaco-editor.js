uifactory.register({
  name: 'monaco-editor',
  template: /* HTML */`<!-- Write the component template -->
  <% var code = this.querySelector('code').innerHTML || '' %>
  <code>
    <%= code %>
  </code>
  <script>
  on('render', 'monaco-editor', function(e) {
    require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.20.0/min/vs' }});
    require(
      ["vs/editor/editor.main"],
      function () {
        if('editor' in e.target) return
        var code = e.target.querySelector('code').textContent.trim()
        e.target.innerHTML = ''
        e.target.editor =
        monaco.editor.create(
          e.target, {
            value: code,
            language: e.target.language || 'html',
            theme: e.target.theme || 'vs-dark',
            automaticLayout: true
          }
        );
    });
    if(!window.MonacoEnvironment) {
      window.MonacoEnvironment = { getWorkerUrl: () => proxy };
      let proxy = URL.createObjectURL(
        new Blob(
          [
            "self.MonacoEnvironment = { " +
                "baseUrl: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.20.0/min'" +
            "};" +
            "importScripts('https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.20.0/min/vs/base/worker/workerMain.min.js');"
          ],
          {
            type: 'text/javascript'
          }
        )
      );
    }
  }, { matchTarget: true })
  </script>
  `,
  options: [
    {
      name: 'value',
      value: 'alert("Hello")'
    },
    {
      name: 'language',
      value: 'javascript'
    },
    {
      name: 'theme',
      value: 'vs-dark'
    }
  ]
})
