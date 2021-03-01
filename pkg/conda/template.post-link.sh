{% for entry in release.pip %}
"$PREFIX/bin/pip" install --use-feature=2020-resolver {% raw entry %}
{% end %}

"$PREFIX/bin/yarn" config set ignore-engines true
"$PREFIX/bin/gramex" setup --all
