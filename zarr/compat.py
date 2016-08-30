# -*- coding: utf-8 -*-
# flake8: noqa
from __future__ import absolute_import, print_function, division
import sys


PY2 = sys.version_info[0] == 2


if PY2:  # pragma: no cover

    text_type = unicode
    binary_type = str
    integer_types = (int, long)
    reduce = reduce

else:

    text_type = str
    binary_type = bytes
    integer_types = int,
    from functools import reduce
