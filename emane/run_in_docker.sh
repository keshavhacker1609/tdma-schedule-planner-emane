#!/bin/sh
# Build the image and run the whole pipeline (planner -> bridge -> EMANE) in one container.
# usage: emane/run_in_docker.sh examples/grid_16.json
set -e
# stop Git Bash on Windows from rewriting /work into a Windows path
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")/.."
INPUT=${1:-examples/grid_16.json}

docker build -t tdma-emane emane
docker run --rm --privileged -e SLOT_US -e BASELINE -v "$PWD":/work -w /work tdma-emane \
    sh emane/container_run.sh "$INPUT"
