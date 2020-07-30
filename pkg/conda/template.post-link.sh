"$CONDA_PREFIX/bin/conda" install -c default rpy2 r-ggplot2 r-rmarkdown -y

{% for entry in release.lib %}
"$CONDA_PREFIX/bin/pip" install "{% raw entry %}"
{% end %}
{% for entry in release.pip %}
"$CONDA_PREFIX/bin/pip" install "{% raw entry %}"
{% end %}

"$CONDA_PREFIX/bin/yarn" config set ignore-engines true
"$CONDA_PREFIX/bin/gramex" setup --all
