#!/usr/bin/env bash

# kill all qgis instances that were launched from this virtual environment
SCRIPTDIR="$( cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd )"
kill $(ps -ef | grep "$CONDA_PREFIX/bin/qgis" | awk '{print $2}')

# add plugin path
. setpath.bash

# actually launch qgis, in the background to allow pycharm to keep going
$CONDA_PREFIX/bin/qgis &
