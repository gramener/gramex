set -ex

npm install
browserify -s tape -r tape -o test/tape.js
cd test
nohup gramex &
echo $! > gramex-pid.txt
sleep 2
node puppet.js | tap-merge | faucet
kill -9 `cat gramex-pid.txt`
cd ..
