#!/usr/bin/env python3

import gevent.monkey
gevent.monkey.patch_ssl()
# gevent monkey patch before importing requests
# detailed info:
# https://github.com/kennethreitz/requests/issues/3752
# __init__.py is possible place to put monkey_patch call
# until the bug is not fixed in the current requests version
