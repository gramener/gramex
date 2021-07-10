# Create test/tape.js dynamically. It's not committed
node_modules/.bin/browserify -s tape -r tape -o test/tape.js

cd test/
rm -rf gramex.log drive*
gramex --listen.port=9999 2>&1 | tee gramex.log &
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
for i in {0..100}
do
  if [[ $(grep 9999 gramex.log) ]]; then
    break
  fi
  sleep 0.2
  echo -n "."
done

# Run test cases
node puppet.js | ../node_modules/.bin/tap-merge | ../node_modules/.bin/faucet
