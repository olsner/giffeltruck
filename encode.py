#!/usr/bin/env python3

import sys
import zlib

data = sys.stdin.buffer.read()
data = zlib.compress(data, level=9)
print(repr(data))
