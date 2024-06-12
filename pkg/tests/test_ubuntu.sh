#!/bin/bash

docker run --rm -it \
  -v $(pwd)/../setup.sh:/app/setup.sh \
  -v $(pwd)/ubuntu.sh:/test/ubuntu.sh \
  -w /test ubuntu:latest \
  bash /test/ubuntu.sh
