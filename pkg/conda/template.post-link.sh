{% for entry in release.lib %}
"$PREFIX/bin/pip" install {% raw entry %}
{% end %}

"$PREFIX/bin/yarn" config set ignore-engines true
"$PREFIX/bin/gramex" setup --all
