{% for entry in release.conda %}
"%PYTHON%" -m pip install --use-feature=2020-resolver {% raw entry %}
{% end %}
"%PYTHON%" -m pip install --use-feature=2020-resolver .
if errorlevel 1 exit 1
