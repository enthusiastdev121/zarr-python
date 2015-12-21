# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division


from nose.tools import eq_ as eq, assert_raises
from zarr.ext import _normalize_cparams
from zarr import defaults


def test_normalize_cparams():

    # defaults
    cname, clevel, shuffle = _normalize_cparams()
    eq(defaults.cname, cname)
    eq(defaults.clevel, clevel)
    eq(defaults.shuffle, shuffle)

    # valid
    cname, clevel, shuffle = _normalize_cparams('zlib', 1, 2)
    eq(b'zlib', cname)
    eq(1, clevel)
    eq(2, shuffle)

    # bad cname
    with assert_raises(ValueError):
        _normalize_cparams('foo', 1, True)

    # bad clevel
    with assert_raises(ValueError):
        _normalize_cparams('zlib', 11, True)

    # bad shuffle
    with assert_raises(ValueError):
        _normalize_cparams('zlib', 1, 3)
