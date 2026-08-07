#!/bin/sh

set -eu

PROJECT_ROOT=$(cd -- "$(dirname -- "$0")" && pwd)/..

## uncomment for resources
#cd "$PROJECT_ROOT"/res
#pyside6-rcc resources.qrc -o resources_rc.py

cd "$PROJECT_ROOT"

rm -rf dist

python3 -m pip install -U pip wheel setuptools
python3 -m pip install -U "nuitka[onefile]"
python3 -m nuitka --onefile --output-dir=dist --assume-yes-for-downloads --enable-plugin=pyside6 src/AnilistToolkit.py
