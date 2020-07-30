"%PREFIX%\Scripts\conda.exe" install -c default rpy2 r-rmarkdown r-ggplot2 -y

{% for entry in release.lib %}
"%PREFIX%\Scripts\pip.exe" install "{% raw entry %}"
{% end %}
{% for entry in release.pip %}
"%PREFIX%\Scripts\pip.exe" install "{% raw entry %}"
{% end %}

call "%PREFIX%\Library\bin\yarn.cmd" config set ignore-engines true
"%PREFIX%\Scripts\gramex.exe" setup --all
if errorlevel 1 exit 1
