# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division
import json
import base64


from nose.tools import eq_ as eq, assert_is_none, assert_raises
import numpy as np


from zarr.compat import binary_type, text_type, PY2
from zarr.meta import (decode_array_metadata, encode_dtype, decode_dtype, ZARR_FORMAT,
                       decode_group_metadata, encode_array_metadata)
from zarr.errors import MetadataError
from zarr.codecs import Delta, Zlib, Blosc


def assert_json_eq(expect, actual):
    if isinstance(expect, binary_type):  # pragma: py3 no cover
        expect = text_type(expect, 'ascii')
    if isinstance(actual, binary_type):
        actual = text_type(actual, 'ascii')
    ej = json.loads(expect)
    aj = json.loads(actual)
    eq(ej, aj)


def test_encode_decode_array_1():

    meta = dict(
        shape=(100,),
        chunks=(10,),
        dtype=np.dtype('f8'),
        compressor=Zlib(1).get_config(),
        fill_value=None,
        filters=None,
        order='C'
    )

    meta_json = '''{
        "chunks": [10],
        "compressor": {"id": "zlib", "level": 1},
        "dtype": "<f8",
        "fill_value": null,
        "filters": null,
        "order": "C",
        "shape": [100],
        "zarr_format": %s
    }''' % ZARR_FORMAT

    # test encoding
    meta_enc = encode_array_metadata(meta)
    assert_json_eq(meta_json, meta_enc)

    # test decoding
    meta_dec = decode_array_metadata(meta_enc)
    eq(ZARR_FORMAT, meta_dec['zarr_format'])
    eq(meta['shape'], meta_dec['shape'])
    eq(meta['chunks'], meta_dec['chunks'])
    eq(meta['dtype'], meta_dec['dtype'])
    eq(meta['compressor'], meta_dec['compressor'])
    eq(meta['order'], meta_dec['order'])
    assert_is_none(meta_dec['fill_value'])
    assert_is_none(meta_dec['filters'])


def test_encode_decode_array_2():

    # some variations
    df = Delta(astype='u2', dtype='V14')
    compressor = Blosc(cname='lz4', clevel=3, shuffle=2)
    meta = dict(
        shape=(100, 100),
        chunks=(10, 10),
        dtype=np.dtype([('a', 'i4'), ('b', 'S10')]),
        compressor=compressor.get_config(),
        fill_value=b'',
        order='F',
        filters=[df.get_config()]
    )

    meta_json = '''{
        "chunks": [10, 10],
        "compressor": {
            "id": "blosc",
            "clevel": 3,
            "cname": "lz4",
            "shuffle": 2,
            "blocksize": 0
        },
        "dtype": [["a", "<i4"], ["b", "|S10"]],
        "fill_value": "",
        "filters": [
            {"id": "delta", "astype": "<u2", "dtype": "|V14"}
        ],
        "order": "F",
        "shape": [100, 100],
        "zarr_format": %s
    }''' % ZARR_FORMAT

    # test encoding
    meta_enc = encode_array_metadata(meta)
    assert_json_eq(meta_json, meta_enc)

    # test decoding
    meta_dec = decode_array_metadata(meta_enc)
    eq(ZARR_FORMAT, meta_dec['zarr_format'])
    eq(meta['shape'], meta_dec['shape'])
    eq(meta['chunks'], meta_dec['chunks'])
    eq(meta['dtype'], meta_dec['dtype'])
    eq(meta['compressor'], meta_dec['compressor'])
    eq(meta['order'], meta_dec['order'])
    np_fill_value = np.array(meta['fill_value'], dtype=meta['dtype'])[()]
    eq(np_fill_value, meta_dec['fill_value'])
    eq([df.get_config()], meta_dec['filters'])


def test_encode_decode_fill_values_nan():

    fills = (
        (np.nan, "NaN", np.isnan),
        (np.NINF, "-Infinity", np.isneginf),
        (np.PINF, "Infinity", np.isposinf),
    )

    for v, s, f in fills:

        meta = dict(
            shape=(100,),
            chunks=(10,),
            dtype=np.dtype('f8'),
            compressor=Zlib(1).get_config(),
            fill_value=v,
            filters=None,
            order='C'
        )

        meta_json = '''{
            "chunks": [10],
            "compressor": {"id": "zlib", "level": 1},
            "dtype": "<f8",
            "fill_value": "%s",
            "filters": null,
            "order": "C",
            "shape": [100],
            "zarr_format": %s
        }''' % (s, ZARR_FORMAT)

        # test encoding
        meta_enc = encode_array_metadata(meta)
        assert_json_eq(meta_json, meta_enc)

        # test decoding
        meta_dec = decode_array_metadata(meta_enc)
        actual = meta_dec['fill_value']
        assert f(actual)


def test_encode_decode_fill_values_bytes():

    dtype = np.dtype('S10')
    fills = b'foo', bytes(10)

    for v in fills:

        # setup and encode metadata
        meta = dict(
            shape=(100,),
            chunks=(10,),
            dtype=dtype,
            compressor=Zlib(1).get_config(),
            fill_value=v,
            filters=None,
            order='C'
        )
        meta_enc = encode_array_metadata(meta)

        # define expected metadata encoded as JSON
        s = base64.standard_b64encode(v)
        if not PY2:
            s = s.decode()
        meta_json = '''{
            "chunks": [10],
            "compressor": {"id": "zlib", "level": 1},
            "dtype": "|S10",
            "fill_value": "%s",
            "filters": null,
            "order": "C",
            "shape": [100],
            "zarr_format": %s
        }''' % (s, ZARR_FORMAT)

        # test encoding
        assert_json_eq(meta_json, meta_enc)

        # test decoding
        meta_dec = decode_array_metadata(meta_enc)
        actual = meta_dec['fill_value']
        expect = np.array(v, dtype=dtype)[()]
        eq(expect, actual)


def test_decode_array_unsupported_format():

    # unsupported format
    meta_json = '''{
        "zarr_format": %s,
        "shape": [100],
        "chunks": [10],
        "dtype": "<f8",
        "compressor": {"id": "zlib", "level": 1},
        "fill_value": null,
        "order": "C"
    }''' % (ZARR_FORMAT - 1)
    with assert_raises(MetadataError):
        decode_array_metadata(meta_json)


def test_decode_array_missing_fields():

    # missing fields
    meta_json = '''{
        "zarr_format": %s
    }''' % ZARR_FORMAT
    with assert_raises(MetadataError):
        decode_array_metadata(meta_json)


def test_encode_decode_dtype():

    for dt in ['f8', [('a', 'f8')], [('a', 'f8'), ('b', 'i1')]]:
        e = encode_dtype(np.dtype(dt))
        s = json.dumps(e)  # check JSON serializable
        o = json.loads(s)
        d = decode_dtype(o)
        eq(np.dtype(dt), d)


def test_decode_group():

    # typical
    b = '''{
        "zarr_format": %s
    }''' % ZARR_FORMAT
    meta = decode_group_metadata(b)
    eq(ZARR_FORMAT, meta['zarr_format'])

    # unsupported format
    b = '''{
        "zarr_format": %s
    }''' % (ZARR_FORMAT - 1)
    with assert_raises(MetadataError):
        decode_group_metadata(b)
