#!/usr/bin/env sh

# Get the directory where the script is located (pytest/)
SCRIPT_DIR=`dirname "$(realpath "$0")"`

# Start Gramex from the pytest directory in GRAMEX_PORT (default: 9999)
PORT=${GRAMEX_PORT:-9999}
cd $SCRIPT_DIR
gramex --listen.port=$PORT &
PID=$!

# Run pytest
GRAMEX_PORT=$PORT pytest
PYTEST_EXIT_CODE=$?

# Kill gramex
kill $PID

# Exit with pytests's exit code
exit $PYTEST_EXIT_CODE
