# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division
import tempfile
import shutil
import atexit
import warnings


import numpy as np
from nose.tools import eq_ as eq, assert_is_none, assert_is_instance, assert_raises
from numpy.testing import assert_array_equal
import pytest


from zarr.creation import (array, empty, zeros, ones, full, open_array, empty_like,
                           zeros_like, ones_like, full_like, open_like, create)
from zarr.sync import ThreadSynchronizer
from zarr.core import Array
from zarr.storage import DirectoryStore
from zarr.hierarchy import open_group
from zarr.errors import PermissionError
from zarr.codecs import Zlib
from zarr.compat import PY2


# needed for PY2/PY3 consistent behaviour
if PY2:  # pragma: py3 no cover
    warnings.resetwarnings()
    warnings.simplefilter('always')


# something bcolz-like
class MockBcolzArray(object):

    def __init__(self, data, chunklen):
        self.data = data
        self.chunklen = chunklen

    def __getattr__(self, item):
        return getattr(self.data, item)

    def __getitem__(self, item):
        return self.data[item]


# something h5py-like
class MockH5pyDataset(object):

    def __init__(self, data, chunks):
        self.data = data
        self.chunks = chunks

    def __getattr__(self, item):
        return getattr(self.data, item)

    def __getitem__(self, item):
        return self.data[item]


def test_array():

    # with numpy array
    a = np.arange(100)
    z = array(a, chunks=10)
    eq(a.shape, z.shape)
    eq(a.dtype, z.dtype)
    assert_array_equal(a, z[:])

    # with array-like
    a = list(range(100))
    z = array(a, chunks=10)
    eq((100,), z.shape)
    eq(np.asarray(a).dtype, z.dtype)
    assert_array_equal(np.asarray(a), z[:])

    # with another zarr array
    z2 = array(z)
    eq(z.shape, z2.shape)
    eq(z.chunks, z2.chunks)
    eq(z.dtype, z2.dtype)
    assert_array_equal(z[:], z2[:])

    # with chunky array-likes

    b = np.arange(1000).reshape(100, 10)
    c = MockBcolzArray(b, 10)
    z3 = array(c)
    eq(c.shape, z3.shape)
    eq((10, 10), z3.chunks)

    b = np.arange(1000).reshape(100, 10)
    c = MockH5pyDataset(b, chunks=(10, 2))
    z4 = array(c)
    eq(c.shape, z4.shape)
    eq((10, 2), z4.chunks)

    c = MockH5pyDataset(b, chunks=None)
    z5 = array(c)
    eq(c.shape, z5.shape)
    assert_is_instance(z5.chunks, tuple)

    # with dtype=None
    a = np.arange(100, dtype='i4')
    z = array(a, dtype=None)
    assert_array_equal(a[:], z[:])
    eq(a.dtype, z.dtype)

    # with dtype=something else
    a = np.arange(100, dtype='i4')
    z = array(a, dtype='i8')
    assert_array_equal(a[:], z[:])
    eq(np.dtype('i8'), z.dtype)


def test_empty():
    z = empty(100, chunks=10)
    eq((100,), z.shape)
    eq((10,), z.chunks)


def test_zeros():
    z = zeros(100, chunks=10)
    eq((100,), z.shape)
    eq((10,), z.chunks)
    assert_array_equal(np.zeros(100), z[:])


def test_ones():
    z = ones(100, chunks=10)
    eq((100,), z.shape)
    eq((10,), z.chunks)
    assert_array_equal(np.ones(100), z[:])


def test_full():
    z = full(100, chunks=10, fill_value=42, dtype='i4')
    eq((100,), z.shape)
    eq((10,), z.chunks)
    assert_array_equal(np.full(100, fill_value=42, dtype='i4'), z[:])

    # nan
    z = full(100, chunks=10, fill_value=np.nan, dtype='f8')
    assert np.all(np.isnan(z[:]))

    # byte string dtype
    v = b'xxx'
    z = full(100, chunks=10, fill_value=v, dtype='S3')
    eq(v, z[0])
    a = z[...]
    eq(z.dtype, a.dtype)
    eq(v, a[0])
    assert np.all(a == v)

    # unicode string dtype
    v = u'xxx'
    z = full(100, chunks=10, fill_value=v, dtype='U3')
    eq(v, z[0])
    a = z[...]
    eq(z.dtype, a.dtype)
    eq(v, a[0])
    assert np.all(a == v)

    # bytes fill value / unicode dtype
    v = b'xxx'
    if PY2:  # pragma: py3 no cover
        # allow this on PY2
        z = full(100, chunks=10, fill_value=v, dtype='U3')
        a = z[...]
        eq(z.dtype, a.dtype)
        eq(v, a[0])
        assert np.all(a == v)
    else:  # pragma: py2 no cover
        # be strict on PY3
        with assert_raises(ValueError):
            full(100, chunks=10, fill_value=v, dtype='U3')


def test_open_array():

    store = 'data/array.zarr'

    # mode == 'w'
    z = open_array(store, mode='w', shape=100, chunks=10)
    z[:] = 42
    assert_is_instance(z, Array)
    assert_is_instance(z.store, DirectoryStore)
    eq((100,), z.shape)
    eq((10,), z.chunks)
    assert_array_equal(np.full(100, fill_value=42), z[:])

    # mode in 'r', 'r+'
    open_group('data/group.zarr', mode='w')
    for mode in 'r', 'r+':
        with assert_raises(ValueError):
            open_array('doesnotexist', mode=mode)
        with assert_raises(ValueError):
            open_array('data/group.zarr', mode=mode)
    z = open_array(store, mode='r')
    assert_is_instance(z, Array)
    assert_is_instance(z.store, DirectoryStore)
    eq((100,), z.shape)
    eq((10,), z.chunks)
    assert_array_equal(np.full(100, fill_value=42), z[:])
    with assert_raises(PermissionError):
        z[:] = 43
    z = open_array(store, mode='r+')
    assert_is_instance(z, Array)
    assert_is_instance(z.store, DirectoryStore)
    eq((100,), z.shape)
    eq((10,), z.chunks)
    assert_array_equal(np.full(100, fill_value=42), z[:])
    z[:] = 43
    assert_array_equal(np.full(100, fill_value=43), z[:])

    # mode == 'a'
    shutil.rmtree(store)
    z = open_array(store, mode='a', shape=100, chunks=10)
    z[:] = 42
    assert_is_instance(z, Array)
    assert_is_instance(z.store, DirectoryStore)
    eq((100,), z.shape)
    eq((10,), z.chunks)
    assert_array_equal(np.full(100, fill_value=42), z[:])
    with assert_raises(ValueError):
        open_array('data/group.zarr', mode='a')

    # mode in 'w-', 'x'
    for mode in 'w-', 'x':
        shutil.rmtree(store)
        z = open_array(store, mode=mode, shape=100, chunks=10)
        z[:] = 42
        assert_is_instance(z, Array)
        assert_is_instance(z.store, DirectoryStore)
        eq((100,), z.shape)
        eq((10,), z.chunks)
        assert_array_equal(np.full(100, fill_value=42), z[:])
        with assert_raises(ValueError):
            open_array(store, mode=mode)
        with assert_raises(ValueError):
            open_array('data/group.zarr', mode=mode)

    # with synchronizer
    z = open_array(store, synchronizer=ThreadSynchronizer())
    assert_is_instance(z, Array)

    # with path
    z = open_array(store, shape=100, path='foo/bar', mode='w')
    assert_is_instance(z, Array)
    eq('foo/bar', z.path)


def test_empty_like():

    # zarr array
    z = empty(100, chunks=10, dtype='f4', compressor=Zlib(5),
              order='F')
    z2 = empty_like(z)
    eq(z.shape, z2.shape)
    eq(z.chunks, z2.chunks)
    eq(z.dtype, z2.dtype)
    eq(z.compressor.get_config(), z2.compressor.get_config())
    eq(z.fill_value, z2.fill_value)
    eq(z.order, z2.order)

    # numpy array
    a = np.empty(100, dtype='f4')
    z3 = empty_like(a)
    eq(a.shape, z3.shape)
    eq((100,), z3.chunks)
    eq(a.dtype, z3.dtype)
    assert_is_none(z3.fill_value)

    # something slightly silly
    a = [0] * 100
    z3 = empty_like(a, shape=200)
    eq((200,), z3.shape)

    # other array-likes
    b = np.arange(1000).reshape(100, 10)
    c = MockBcolzArray(b, 10)
    z = empty_like(c)
    eq(b.shape, z.shape)
    eq((10, 10), z.chunks)
    c = MockH5pyDataset(b, chunks=(10, 2))
    z = empty_like(c)
    eq(b.shape, z.shape)
    eq((10, 2), z.chunks)
    c = MockH5pyDataset(b, chunks=None)
    z = empty_like(c)
    eq(b.shape, z.shape)
    assert_is_instance(z.chunks, tuple)


def test_zeros_like():
    # zarr array
    z = zeros(100, chunks=10, dtype='f4', compressor=Zlib(5),
              order='F')
    z2 = zeros_like(z)
    eq(z.shape, z2.shape)
    eq(z.chunks, z2.chunks)
    eq(z.dtype, z2.dtype)
    eq(z.compressor.get_config(), z2.compressor.get_config())
    eq(z.fill_value, z2.fill_value)
    eq(z.order, z2.order)
    # numpy array
    a = np.empty(100, dtype='f4')
    z3 = zeros_like(a, chunks=10)
    eq(a.shape, z3.shape)
    eq((10,), z3.chunks)
    eq(a.dtype, z3.dtype)
    eq(0, z3.fill_value)


def test_ones_like():
    # zarr array
    z = ones(100, chunks=10, dtype='f4', compressor=Zlib(5),
             order='F')
    z2 = ones_like(z)
    eq(z.shape, z2.shape)
    eq(z.chunks, z2.chunks)
    eq(z.dtype, z2.dtype)
    eq(z.compressor.get_config(), z2.compressor.get_config())
    eq(z.fill_value, z2.fill_value)
    eq(z.order, z2.order)
    # numpy array
    a = np.empty(100, dtype='f4')
    z3 = ones_like(a, chunks=10)
    eq(a.shape, z3.shape)
    eq((10,), z3.chunks)
    eq(a.dtype, z3.dtype)
    eq(1, z3.fill_value)


def test_full_like():
    z = full(100, chunks=10, dtype='f4', compressor=Zlib(5),
             fill_value=42, order='F')
    z2 = full_like(z)
    eq(z.shape, z2.shape)
    eq(z.chunks, z2.chunks)
    eq(z.dtype, z2.dtype)
    eq(z.compressor.get_config(), z2.compressor.get_config())
    eq(z.fill_value, z2.fill_value)
    eq(z.order, z2.order)
    # numpy array
    a = np.empty(100, dtype='f4')
    z3 = full_like(a, chunks=10, fill_value=42)
    eq(a.shape, z3.shape)
    eq((10,), z3.chunks)
    eq(a.dtype, z3.dtype)
    eq(42, z3.fill_value)
    with assert_raises(TypeError):
        # fill_value missing
        full_like(a, chunks=10)


def test_open_like():
    # zarr array
    path = tempfile.mktemp()
    atexit.register(shutil.rmtree, path)
    z = full(100, chunks=10, dtype='f4', compressor=Zlib(5),
             fill_value=42, order='F')
    z2 = open_like(z, path)
    eq(z.shape, z2.shape)
    eq(z.chunks, z2.chunks)
    eq(z.dtype, z2.dtype)
    eq(z.compressor.get_config(), z2.compressor.get_config())
    eq(z.fill_value, z2.fill_value)
    eq(z.order, z2.order)
    # numpy array
    path = tempfile.mktemp()
    atexit.register(shutil.rmtree, path)
    a = np.empty(100, dtype='f4')
    z3 = open_like(a, path, chunks=10)
    eq(a.shape, z3.shape)
    eq((10,), z3.chunks)
    eq(a.dtype, z3.dtype)
    eq(0, z3.fill_value)


def test_create():

    # defaults
    z = create(100)
    assert_is_instance(z, Array)
    eq((100,), z.shape)
    eq((100,), z.chunks)  # auto-chunks
    eq(np.dtype(None), z.dtype)
    eq('blosc', z.compressor.codec_id)
    eq(0, z.fill_value)

    # all specified
    z = create(100, chunks=10, dtype='i4', compressor=Zlib(1),
               fill_value=42, order='F')
    assert_is_instance(z, Array)
    eq((100,), z.shape)
    eq((10,), z.chunks)
    eq(np.dtype('i4'), z.dtype)
    eq('zlib', z.compressor.codec_id)
    eq(1, z.compressor.level)
    eq(42, z.fill_value)
    eq('F', z.order)

    # with synchronizer
    synchronizer = ThreadSynchronizer()
    z = create(100, chunks=10, synchronizer=synchronizer)
    assert_is_instance(z, Array)
    eq((100,), z.shape)
    eq((10,), z.chunks)
    assert synchronizer is z.synchronizer

    # don't allow string as compressor arg
    with assert_raises(ValueError):
        create(100, chunks=10, compressor='zlib')

    # h5py compatibility

    z = create(100, compression='zlib', compression_opts=9)
    eq('zlib', z.compressor.codec_id)
    eq(9, z.compressor.level)

    z = create(100, compression='default')
    eq('blosc', z.compressor.codec_id)

    # errors
    with assert_raises(ValueError):
        # bad compression argument
        create(100, compression=1)
    with assert_raises(ValueError):
        # bad fill value
        create(100, dtype='i4', fill_value='foo')

    # auto chunks
    z = create(1000000000, chunks=True)
    assert z.chunks[0] < z.shape[0]
    z = create(1000000000, chunks=None)  # backwards-compatibility
    assert z.chunks[0] < z.shape[0]
    # no chunks
    z = create(1000000000, chunks=False)
    assert z.chunks == z.shape


def test_compression_args():

    z = create(100, compression='zlib', compression_opts=9)
    assert_is_instance(z, Array)
    eq('zlib', z.compressor.codec_id)
    eq(9, z.compressor.level)

    # 'compressor' overrides 'compression'
    z = create(100, compressor=Zlib(9), compression='bz2', compression_opts=1)
    assert_is_instance(z, Array)
    eq('zlib', z.compressor.codec_id)
    eq(9, z.compressor.level)

    # 'compressor' ignores 'compression_opts'
    z = create(100, compressor=Zlib(9), compression_opts=1)
    assert_is_instance(z, Array)
    eq('zlib', z.compressor.codec_id)
    eq(9, z.compressor.level)

    with pytest.warns(UserWarning):
        # 'compressor' overrides 'compression'
        create(100, compressor=Zlib(9), compression='bz2', compression_opts=1)
    with pytest.warns(UserWarning):
        # 'compressor' ignores 'compression_opts'
        create(100, compressor=Zlib(9), compression_opts=1)


def test_create_read_only():
    # https://github.com/alimanfoo/zarr/issues/151

    # create an array initially read-only, then enable writing
    z = create(100, read_only=True)
    assert z.read_only
    with assert_raises(PermissionError):
        z[:] = 42
    z.read_only = False
    z[:] = 42
    assert np.all(z[...] == 42)
    z.read_only = True
    with assert_raises(PermissionError):
        z[:] = 0

    # this is subtly different, but here we want to create an array with data, and then
    # have it be read-only
    a = np.arange(100)
    z = array(a, read_only=True)
    assert_array_equal(a, z[...])
    assert z.read_only
    with assert_raises(PermissionError):
        z[:] = 42
