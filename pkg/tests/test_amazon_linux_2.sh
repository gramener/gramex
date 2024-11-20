#!/bin/bash

docker run --rm -it \
  -v $(pwd)/../setup.sh:/app/setup.sh \
  -v $(pwd)/amazon_linux_2.sh:/test/amazon_linux_2.sh \
  -w /test amazonlinux:2 \
  bash /test/amazon_linux_2.sh
