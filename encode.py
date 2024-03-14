#!/usr/bin/env python3

import sys
import zlib

data = sys.stdin.buffer.read()
# Strip final newline to avoid empty line at end
# NB: screen "layouts" might depend on the extra newline at the end of the
# home screen and level data, double-check when updating data next time.
if data[-1] == 10:
    data = data[:-1]
print(repr(data))
print(repr(data.decode('utf8').split('\n')))
data = zlib.compress(data, level=9)
print(repr(data))
