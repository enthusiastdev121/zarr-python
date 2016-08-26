# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division
import json


import numpy as np


from zarr.compat import PY2, text_type, binary_type
from zarr.errors import MetadataError


ZARR_FORMAT = 2


def decode_array_metadata(s):
    if isinstance(s, binary_type):
        s = text_type(s, 'ascii')
    meta = json.loads(s)
    zarr_format = meta.get('zarr_format', None)
    if zarr_format != ZARR_FORMAT:
        raise MetadataError('unsupported zarr format: %s' % zarr_format)
    try:
        meta = dict(
            zarr_format=meta['zarr_format'],
            shape=tuple(meta['shape']),
            chunks=tuple(meta['chunks']),
            dtype=decode_dtype(meta['dtype']),
            compression=meta['compression'],
            compression_opts=meta['compression_opts'],
            fill_value=meta['fill_value'],
            order=meta['order'],
        )
    except Exception as e:
        raise MetadataError('error decoding metadata: %s' % e)
    else:
        return meta


def encode_array_metadata(meta):
    meta = dict(
        zarr_format=ZARR_FORMAT,
        shape=meta['shape'],
        chunks=meta['chunks'],
        dtype=encode_dtype(meta['dtype']),
        compression=meta['compression'],
        compression_opts=meta['compression_opts'],
        fill_value=meta['fill_value'],
        order=meta['order'],
    )
    s = json.dumps(meta, indent=4, sort_keys=True, ensure_ascii=True)
    b = s.encode('ascii')
    return b


def encode_dtype(d):
    if d.fields is None:
        return d.str
    else:
        return d.descr


def _decode_dtype_descr(d):
    # need to convert list of lists to list of tuples
    if isinstance(d, list):
        # recurse to handle nested structures
        if PY2:  # pragma: no cover
            # under PY2 numpy rejects unicode field names
            d = [(f.encode('ascii'), _decode_dtype_descr(v))
                 for f, v in d]
        else:
            d = [(f, _decode_dtype_descr(v)) for f, v in d]
    return d


def decode_dtype(d):
    d = _decode_dtype_descr(d)
    return np.dtype(d)


def decode_group_metadata(s):
    if isinstance(s, binary_type):
        s = text_type(s, 'ascii')
    meta = json.loads(s)
    zarr_format = meta.get('zarr_format', None)
    if zarr_format != ZARR_FORMAT:
        raise MetadataError('unsupported zarr format: %s' % zarr_format)
    meta = dict(
        zarr_format=ZARR_FORMAT,
    )
    return meta


def encode_group_metadata(meta=None):
    meta = dict(
        zarr_format=ZARR_FORMAT,
    )
    s = json.dumps(meta, indent=4, sort_keys=True, ensure_ascii=True)
    b = s.encode('ascii')
    return b
