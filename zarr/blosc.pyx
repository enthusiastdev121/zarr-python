# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division


import sys
import ctypes
# noinspection PyUnresolvedReferences
import numpy as np
cimport numpy as np
# noinspection PyUnresolvedReferences
from libc.stdint cimport uintptr_t
# noinspection PyUnresolvedReferences
from .definitions cimport malloc, realloc, free, PyBytes_AsString


PY2 = sys.version_info[0] == 2


cdef extern from "blosc.h":
    cdef enum:
        BLOSC_MAX_OVERHEAD,
        BLOSC_VERSION_STRING,
        BLOSC_VERSION_DATE

    void blosc_init()
    void blosc_destroy()
    int blosc_set_nthreads(int nthreads)
    int blosc_set_compressor(const char *compname)
    int blosc_compress(int clevel, int doshuffle, size_t typesize,
                       size_t nbytes, void *src, void *dest,
                       size_t destsize) nogil
    int blosc_decompress(void *src, void *dest, size_t destsize) nogil
    int blosc_compname_to_compcode(const char *compname)
    int blosc_compress_ctx(int clevel, int doshuffle, size_t typesize,
                           size_t nbytes, const void* src, void* dest,
                           size_t destsize, const char* compressor,
				           size_t blocksize, int numinternalthreads) nogil
    int blosc_decompress_ctx(const void *src, void *dest, size_t destsize,
                             int numinternalthreads) nogil
    void blosc_cbuffer_sizes(void *cbuffer, size_t *nbytes,
                             size_t *cbytes, size_t *blocksize)


def version():
    """Return the version of blosc that zarr was compiled with."""

    ver_str = <char*> BLOSC_VERSION_STRING
    ver_date = <char*> BLOSC_VERSION_DATE
    if not PY2:
        ver_str = ver_str.decode()
        ver_date = ver_date.decode()
    return ver_str, ver_date


def init():
    blosc_init()


def destroy():
    blosc_destroy()


def compname_to_compcode(cname):
    if not isinstance(cname, bytes):
        cname = cname.encode('ascii')
    ccode = blosc_compname_to_compcode(cname)
    if ccode < 0:
        raise ValueError('compressor not available: %r' % cname)
    return ccode


def decompress(bytes cdata, np.ndarray array, use_context):
    """Decompress data into a numpy array.

    Parameters
    ----------
    cdata : bytes
        Compressed data, including blosc header.
    array : ndarray
        Numpy array to decompress into.
    use_context : bool
        If True, use blosc contextual mode. Otherwise use global locking mode.

    Notes
    -----
    Assumes that the size of the destination array is correct for the size of
    the uncompressed data.

    """

    cdef:
        int ret
        char* source
        char* dest
        size_t nbytes

    # setup
    source = PyBytes_AsString(cdata)
    dest = array.data
    nbytes = array.nbytes

    # perform decompression
    if use_context:
        with nogil:
            ret = blosc_decompress_ctx(source, dest, nbytes, 1)

    else:
        ret = blosc_decompress(source, dest, nbytes)

    # handle errors
    if ret <= 0:
        raise RuntimeError('error during blosc decompression: %d' % ret)


def compress(np.ndarray array, char* cname, int clevel, int shuffle,
             use_context):
    """Compress data in a numpy array.

    Parameters
    ----------
    array : ndarray
        Numpy array containing data to be compressed.
    cname : bytes
        Name of compression library to use.
    clevel : int
        Compression level.
    shuffle : int
        Shuffle filter.
    use_context : bool
        If True, use blosc contextual mode. Otherwise use global locking mode.

    Returns
    -------
    cdata : bytes
        Compressed data.

    """

    cdef:
        char* source
        char* dest
        char* cdata
        size_t nbytes, cbytes, itemsize
        bytes cdata_bytes

    # obtain reference to underlying buffer
    source = array.data

    # allocate memory for compressed data
    nbytes = array.nbytes
    itemsize = array.dtype.itemsize
    dest = <char*> malloc(nbytes + BLOSC_MAX_OVERHEAD)

    # perform compression
    if use_context:
        with nogil:
            cbytes = blosc_compress_ctx(clevel, shuffle, itemsize, nbytes,
                                        source, dest,
                                        nbytes + BLOSC_MAX_OVERHEAD, cname,
                                        0, 1)

    else:
        compressor_set = blosc_set_compressor(cname)
        if compressor_set < 0:
            raise ValueError('compressor not supported: %r' % cname)
        cbytes = blosc_compress(clevel, shuffle, itemsize, nbytes, source,
                                dest, nbytes + BLOSC_MAX_OVERHEAD)

    # check compression was successful
    if cbytes <= 0:
        raise RuntimeError('error during blosc compression: %d' % cbytes)

    # free the unused memory
    cdata = <char*> realloc(dest, cbytes)

    # store as bytes
    cdata_bytes = ctypes.string_at(<uintptr_t> cdata, cbytes)

    return cdata_bytes
