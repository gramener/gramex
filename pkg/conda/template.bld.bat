{% for entry in release.pip %}
"%PYTHON%" -m pip install --use-feature=2020-resolver {% raw entry %}
{% end %}
"%PYTHON%" -m pip install --use-feature=2020-resolver .
if errorlevel 1 exit 1
