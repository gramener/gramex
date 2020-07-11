# Create test/tape.js dynamically. It's not committed
browserify -s tape -r tape -o test/tape.js

cd test/
rm -f gramex.log
gramex --listen.port=9999 > gramex.log 2>&1 &
GRAMEX_PID=$!
# Kill gramex when process exits. Note: Doesn't kill Gramex on Cygwin
trap "kill $GRAMEX_PID" SIGINT SIGTERM EXIT

# Wait until Gramex starts at port 9999
until grep 9999 gramex.log; do sleep 0.2; done

# Run test cases
node puppet.js | tap-merge | faucet
