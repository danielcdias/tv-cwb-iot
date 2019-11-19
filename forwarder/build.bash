#!/bin/bash
rm -r -f dist
rm -r -f build
rm -r -f __pycache__
pyinstaller -F forwarder.py --clean
