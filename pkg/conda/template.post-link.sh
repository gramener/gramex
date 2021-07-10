{% for entry in release.pip %}
"$PREFIX/bin/pip" install {% raw entry %}
{% end %}

"$PREFIX/bin/yarn" config set ignore-engines true
"$PREFIX/bin/gramex" setup --all
