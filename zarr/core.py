# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division


import numpy as np


import zarr.ext as _ext


def empty(shape, chunks, dtype=None, cname=None, clevel=None, shuffle=None,
          synchronized=True):
    """Create an empty array.

    Parameters
    ----------
    shape : int or tuple of ints
        Array shape.
    chunks : int or tuple of ints
        Chunk shape.
    dtype : string or dtype, optional
        NumPy dtype.
    cname : string, optional
        Name of compression library to use, e.g., 'blosclz', 'lz4', 'zlib',
        'snappy'.
    clevel : int, optional
        Compression level, 0 means no compression.
    shuffle : int, optional
        Shuffle filter, 0 means no shuffle, 1 means byte shuffle, 2 means
        bit shuffle.
    synchronized : bool, optional
        If True, each chunk will be protected with a lock to prevent data
        collision during concurrent write operations.

    Returns
    -------
    z : zarr Array

    """

    if synchronized:
        cls = _ext.SynchronizedArray
    else:
        cls = _ext.Array
    return cls(shape=shape, chunks=chunks, dtype=dtype, cname=cname,
               clevel=clevel, shuffle=shuffle)


def zeros(shape, chunks, dtype=None, cname=None, clevel=None, shuffle=None,
          synchronized=True):
    """Create an array, with zero being used as the default value for
    uninitialised portions of the array.

    Parameters
    ----------
    shape : int or tuple of ints
        Array shape.
    chunks : int or tuple of ints
        Chunk shape.
    dtype : string or dtype, optional
        NumPy dtype.
    cname : string, optional
        Name of compression library to use, e.g., 'blosclz', 'lz4', 'zlib',
        'snappy'.
    clevel : int, optional
        Compression level, 0 means no compression.
    shuffle : int, optional
        Shuffle filter, 0 means no shuffle, 1 means byte shuffle, 2 means
        bit shuffle.
    synchronized : bool, optional
        If True, each chunk will be protected with a lock to prevent data
        collision during concurrent write operations.

    Returns
    -------
    z : zarr Array

    """

    if synchronized:
        cls = _ext.SynchronizedArray
    else:
        cls = _ext.Array
    return cls(shape=shape, chunks=chunks, dtype=dtype, cname=cname,
               clevel=clevel, shuffle=shuffle, fill_value=0)


def ones(shape, chunks, dtype=None, cname=None, clevel=None, shuffle=None,
         synchronized=True):
    """Create an array, with one being used as the default value for
    uninitialised portions of the array.

    Parameters
    ----------
    shape : int or tuple of ints
        Array shape.
    chunks : int or tuple of ints
        Chunk shape.
    dtype : string or dtype, optional
        NumPy dtype.
    cname : string, optional
        Name of compression library to use, e.g., 'blosclz', 'lz4', 'zlib',
        'snappy'.
    clevel : int, optional
        Compression level, 0 means no compression.
    shuffle : int, optional
        Shuffle filter, 0 means no shuffle, 1 means byte shuffle, 2 means
        bit shuffle.
    synchronized : bool, optional
        If True, each chunk will be protected with a lock to prevent data
        collision during write operations.

    Returns
    -------
    z : zarr Array

    """

    if synchronized:
        cls = _ext.SynchronizedArray
    else:
        cls = _ext.Array
    return cls(shape=shape, chunks=chunks, dtype=dtype, cname=cname,
               clevel=clevel, shuffle=shuffle, fill_value=1)


def full(shape, chunks, fill_value, dtype=None, cname=None, clevel=None,
         shuffle=None, synchronized=True):
    """Create an array, with `fill_value` being used as the default value for
    uninitialised portions of the array.

    Parameters
    ----------
    shape : int or tuple of ints
        Array shape.
    chunks : int or tuple of ints
        Chunk shape.
    fill_value : object
        Default value to use for uninitialised portions of the array.
    dtype : string or dtype, optional
        NumPy dtype.
    cname : string, optional
        Name of compression library to use, e.g., 'blosclz', 'lz4', 'zlib',
        'snappy'.
    clevel : int, optional
        Compression level, 0 means no compression.
    shuffle : int, optional
        Shuffle filter, 0 means no shuffle, 1 means byte shuffle, 2 means
        bit shuffle.
    synchronized : bool, optional
        If True, each chunk will be protected with a lock to prevent data
        collision during write operations.

    Returns
    -------
    z : zarr Array

    """

    if synchronized:
        cls = _ext.SynchronizedArray
    else:
        cls = _ext.Array
    return cls(shape=shape, chunks=chunks, dtype=dtype, cname=cname,
               clevel=clevel, shuffle=shuffle, fill_value=fill_value)


def array(data, chunks=None, dtype=None, cname=None, clevel=None,
          shuffle=None, fill_value=None, synchronized=True):
    """Create an array filled with `data`.

    Parameters
    ----------
    data : array_like
        Data to store.
    chunks : int or tuple of ints
        Chunk shape.
    dtype : string or dtype, optional
        NumPy dtype.
    cname : string, optional
        Name of compression library to use, e.g., 'blosclz', 'lz4', 'zlib',
        'snappy'.
    clevel : int, optional
        Compression level, 0 means no compression.
    shuffle : int, optional
        Shuffle filter, 0 means no shuffle, 1 means byte shuffle, 2 means
        bit shuffle.
    fill_value : object
        Default value to use for uninitialised portions of the array.
    synchronized : bool, optional
        If True, each chunk will be protected with a lock to prevent data
        collision during write operations.

    Returns
    -------
    z : zarr Array

    """

    # ensure data is array-like
    if not hasattr(data, 'shape') or not hasattr(data, 'dtype'):
        data = np.asanyarray(data)

    # setup dtype
    if dtype is None:
        dtype = data.dtype

    # setup shape
    shape = data.shape

    # setup chunks
    if chunks is None:
        if hasattr(data, 'chunklen'):
            # bcolz carray
            chunks = (data.chunklen,) + shape[1:]
        elif hasattr(data, 'chunks') and len(data.chunks) == len(data.shape):
            # h5py dataset or zarr array
            chunks = data.chunks
        else:
            raise ValueError('chunks must be specified')

    # create array
    if synchronized:
        cls = _ext.SynchronizedArray
    else:
        cls = _ext.Array
    z = cls(shape=shape, chunks=chunks, dtype=dtype, cname=cname,
            clevel=clevel, shuffle=shuffle, fill_value=fill_value)

    # fill with data
    z[:] = data

    return z


# noinspection PyShadowingBuiltins
def open(path, mode='a', shape=None, chunks=None, dtype=None, cname=None,
         clevel=None, shuffle=None, fill_value=None, synchronized=True):
    """Open a persistent array.

    Parameters
    ----------
    path : string
        Path to directory in which to store the array.
    mode : {'r', 'r+', 'a', 'w', 'w-'}
        Persistence mode: 'r' means readonly (must exist); 'r+' means
        read/write (must exist); 'a' means read/write (create if doesn't
        exist); 'w' means create (overwrite if exists); 'w-' means create
        (fail if exists).
    shape : int or tuple of ints
        Array shape.
    chunks : int or tuple of ints
        Chunk shape.
    dtype : string or dtype, optional
        NumPy dtype.
    cname : string, optional
        Name of compression library to use, e.g., 'blosclz', 'lz4', 'zlib',
        'snappy'.
    clevel : int, optional
        Compression level, 0 means no compression.
    shuffle : int, optional
        Shuffle filter, 0 means no shuffle, 1 means byte shuffle, 2 means
        bit shuffle.
    fill_value : object
        Default value to use for uninitialised portions of the array.
    synchronized : bool, optional
        If True, each chunk will be protected with a lock to prevent data
        collision during write operations.

    Returns
    -------
    z : zarr Array

    """

    if synchronized:
        cls = _ext.SynchronizedPersistentArray
    else:
        cls = _ext.PersistentArray
    return cls(path=path, mode=mode, shape=shape, chunks=chunks, dtype=dtype,
               cname=cname, clevel=clevel, shuffle=shuffle,
               fill_value=fill_value)
