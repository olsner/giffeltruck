#!/usr/bin/env python3

import sys
import zlib

data = sys.stdin.buffer.read()
print(repr(data))
print(repr(data.decode('ascii').split('\n')))
data = zlib.compress(data, level=9)
print(repr(data))
