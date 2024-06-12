#!/bin/bash

docker run --rm -it \
  -v $(pwd)/../setup.sh:/app/setup.sh \
  -v $(pwd)/centos7.sh:/test/centos7.sh \
  -w /test centos:7 \
  bash /test/centos7.sh
