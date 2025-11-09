#!/bin/bash

docker build \
-f docker/Dockerfile.prod \
-t gplot_prod:latest \
.