{% for entry in release.lib %}
"%PREFIX%\Scripts\pip.exe" install --use-feature=2020-resolver "{% raw entry %}"
{% end %}

{% for entry in release.pip %}
"%PREFIX%\Scripts\pip.exe" install --use-feature=2020-resolver "{% raw entry %}"
{% end %}

if errorlevel 1 exit 1
