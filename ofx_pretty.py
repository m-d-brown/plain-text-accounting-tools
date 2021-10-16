#!/usr/bin/env python3.9
# 3.9 is needed for ElementTree.indent

"""ofx_pretty takes a path to an OFX file as the first argument
and prints a prettified version to stdout. It does not yet
include the metadata at the start of the file! You'll have to
copy that yourself.
"""

import sys
import xml.etree.ElementTree as ET

# https://ofxtools.readthedocs.io/en/latest/parser.html
from ofxtools.Parser import OFXTree

parser = OFXTree()
parser.parse(sys.argv[1])
ET.indent(parser._root)
parser.write(sys.stdout.buffer)

