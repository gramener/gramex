{% for entry in release.pip %}
"%PREFIX%\Scripts\pip.exe" install --use-feature=2020-resolver "{% raw entry %}"
{% end %}

call "%PREFIX%\Library\bin\yarn.cmd" config set ignore-engines true
"%PREFIX%\Scripts\gramex.exe" setup --all > %PREFIX%\.messages.txt 2>&1
if errorlevel 1 exit 1
