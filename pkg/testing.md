# Testing setup

To test this on Ubuntu:

```bash
docker run -it --rm -v $(pwd):/app -w /app ubuntu bash

# add user
./pkg/setup.sh
```
