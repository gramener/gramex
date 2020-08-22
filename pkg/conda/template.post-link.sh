{% for entry in release.lib %}
"$CONDA_PREFIX/bin/pip" install --use-feature=2020-resolver "{% raw entry %}"
{% end %}
{% for entry in release.pip %}
"$CONDA_PREFIX/bin/pip" install --use-feature=2020-resolver "{% raw entry %}"
{% end %}

"$CONDA_PREFIX/bin/yarn" config set ignore-engines true
"$CONDA_PREFIX/bin/gramex" setup --all
