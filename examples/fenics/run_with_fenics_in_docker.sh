#!/bin/bash

# creates a volume for caching pip packages
if ! docker volume inspect pip-cache > /dev/null; then
  echo "Creating docker volume pip-cache"
  docker volume create --name pip-cache
fi

docker run --rm --entrypoint /bin/bash \
           -v pip-cache:/root/.cache/pip \
           -v $(pwd):/home/fenics/shared \
           -w /home/fenics/shared dolfinx/dolfinx:stable \
           -c "python3 -m pip install fieldcompare[all] && python3 $@"
