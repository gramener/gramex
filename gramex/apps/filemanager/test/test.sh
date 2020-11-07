# Create test/tape.js dynamically. It's not committed
browserify -s tape -r tape -o test/tape.js

cd test/
rm -rf gramex.log drive*
gramex --listen.port=9999 > gramex.log 2>&1 &
GRAMEX_PID=$!

# Kill gramex when process exits
case "$(uname -s)" in
    # Cygwin requires the windows process ID.
    CYGWIN*)
        # ps -W gets Windows PIDs.
        # grep the first Python (hopefully the only one). grep & print all numbers and pick the head
        WIN_PID=`ps -W | grep python | grep -o -E '[0-9]+' | head -1`
        # Bash has a kill. But Cygwin also has a kill. Use THAT one
        trap "/bin/kill -f $WIN_PID" SIGINT SIGTERM EXIT
        ;;
    Linux)
        # Use bash kill to kill Gramex
        trap "kill $GRAMEX_PID" SIGINT SIGTERM EXIT
        ;;
esac

# Wait until Gramex starts at port 9999
until grep 9999 gramex.log; do sleep 0.2; done

# Run test cases
node puppet.js | tap-merge | faucet
