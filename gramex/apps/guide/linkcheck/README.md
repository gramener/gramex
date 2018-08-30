---
title: Guide self test
prefix: Self Test
...

<style>
  .content a, .content a:visited { color: #444; }
  .content .ok, .content .ok:visited { color: #28a745; }
  .content .fail, .content .fail:visited { color: #dc3545; }
  .content .fail span { color: #000; }
</style>

Checks if the Gramex guide links are OK. Click "Check" to start checking.

<form>
  <input id="url" value="../" placeholder="URL to start checking from">
  <select id="depth">
    <option value="1">Depth 1: Check just the page</option>
    <option value="2">Depth 2: Check page links</option>
    <option value="3" selected>Depth 3: links from links</option>
  </select>
  <button type="submit">Start checking</button>
</form>

<span class="ok">Green links are OK</span>.
<span class="fail">Red links have failed</span>

<ul class="linkcheck"></ul>

<script src="linkcheck.js?v=1"></script>
<script>
  $('form').on('submit', function(e) {
    e.preventDefault()
    $('.linkcheck').linkcheck($('#url').val(), +$('#depth').val())
  })
</script>
