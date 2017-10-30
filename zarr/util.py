# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division
import operator
from textwrap import TextWrapper
import numbers
import functools


import numpy as np


from zarr.compat import PY2, reduce


def normalize_shape(shape):
    """Convenience function to normalize the `shape` argument."""

    if shape is None:
        raise TypeError('shape is None')

    # handle 1D convenience form
    if isinstance(shape, numbers.Integral):
        shape = (int(shape),)

    # normalize
    shape = tuple(int(s) for s in shape)
    return shape


# code to guess chunk shape, adapted from h5py

CHUNK_BASE = 64*1024  # Multiplier by which chunks are adjusted
CHUNK_MIN = 128*1024  # Soft lower limit (128k)
CHUNK_MAX = 16*1024*1024  # Hard upper limit (16M)


def guess_chunks(shape, typesize):
    """
    Guess an appropriate chunk layout for a dataset, given its shape and
    the size of each element in bytes.  Will allocate chunks only as large
    as MAX_SIZE.  Chunks are generally close to some power-of-2 fraction of
    each axis, slightly favoring bigger values for the last index.
    Undocumented and subject to change without warning.
    """

    ndims = len(shape)
    # require chunks to have non-zero length for all dimensions
    chunks = np.maximum(np.array(shape, dtype='=f8'), 1)

    # Determine the optimal chunk size in bytes using a PyTables expression.
    # This is kept as a float.
    dset_size = np.product(chunks)*typesize
    target_size = CHUNK_BASE * (2**np.log10(dset_size/(1024.*1024)))

    if target_size > CHUNK_MAX:
        target_size = CHUNK_MAX
    elif target_size < CHUNK_MIN:
        target_size = CHUNK_MIN

    idx = 0
    while True:
        # Repeatedly loop over the axes, dividing them by 2.  Stop when:
        # 1a. We're smaller than the target chunk size, OR
        # 1b. We're within 50% of the target chunk size, AND
        # 2. The chunk is smaller than the maximum chunk size

        chunk_bytes = np.product(chunks)*typesize

        if (chunk_bytes < target_size or
                abs(chunk_bytes-target_size)/target_size < 0.5) and \
                chunk_bytes < CHUNK_MAX:
            break

        if np.product(chunks) == 1:
            break  # Element size larger than CHUNK_MAX

        chunks[idx % ndims] = np.ceil(chunks[idx % ndims] / 2.0)
        idx += 1

    return tuple(int(x) for x in chunks)


def normalize_chunks(chunks, shape, typesize):
    """Convenience function to normalize the `chunks` argument for an array
    with the given `shape`."""

    # N.B., expect shape already normalized

    # handle auto-chunking
    if chunks is None or chunks is True:
        return guess_chunks(shape, typesize)

    # handle 1D convenience form
    if isinstance(chunks, numbers.Integral):
        chunks = (int(chunks),)

    # handle bad dimensionality
    if len(chunks) > len(shape):
        raise ValueError('too many dimensions in chunks')

    # handle underspecified chunks
    if len(chunks) < len(shape):
        # assume chunks across remaining dimensions
        chunks += shape[len(chunks):]

    # handle None in chunks
    chunks = tuple(s if c is None else int(c)
                   for s, c in zip(shape, chunks))

    return chunks


# noinspection PyTypeChecker
def is_total_slice(item, shape):
    """Determine whether `item` specifies a complete slice of array with the
    given `shape`. Used to optimize __setitem__ operations on the Chunk
    class."""

    # N.B., assume shape is normalized

    if item == Ellipsis:
        return True
    if item == slice(None):
        return True
    if isinstance(item, slice):
        item = item,
    if isinstance(item, tuple):
        return all(
            (isinstance(s, slice) and
                ((s == slice(None)) or
                 ((s.stop - s.start == l) and (s.step in [1, None]))))
            for s, l in zip(item, shape)
        )
    else:
        raise TypeError('expected slice or tuple of slices, found %r' % item)


class BooleanSelection(object):

    def __init__(self, dim_sel, dim_len, dim_chunk_len):

        # check number of dimensions, only support indexing with 1d array
        if len(dim_sel.shape) > 1:
            raise IndexError('can only index with 1-dimensional Boolean array')

        # check shape
        if dim_sel.shape[0] != dim_len:
            raise IndexError('Boolean array has wrong length; expected %s, found %s' %
                             (dim_len, dim_sel.shape[0]))

        self.dim_sel = dim_sel
        self.dim_len = dim_len
        self.dim_chunk_len = dim_chunk_len
        self.nchunks = int(np.ceil(self.dim_len / self.dim_chunk_len))

    def __getitem__(self, item):
        return self.dim_sel[item]

    def get_chunk_sel(self, dim_chunk_idx):
        dim_chunk_offset = dim_chunk_idx * self.dim_chunk_len
        return self.dim_sel[dim_chunk_offset:dim_chunk_offset + self.dim_chunk_len]

    def get_out_sel(self, dim_chunk_idx):
        dim_out_offset = self.get_sel_offset(dim_chunk_idx)
        dim_chunk_nitems = self.get_chunk_nitems(dim_chunk_idx)
        return slice(dim_out_offset, dim_out_offset + dim_chunk_nitems)

    @functools.lru_cache(maxsize=None)
    def get_chunk_nitems(self, dim_chunk_idx):
        dim_chunk_sel = self.get_chunk_sel(dim_chunk_idx)
        return np.count_nonzero(dim_chunk_sel)

    @functools.lru_cache(maxsize=None)
    def get_nitems(self):
        return sum(self.get_chunk_nitems(i) for i in range(self.nchunks))

    @functools.lru_cache(maxsize=None)
    def get_sel_offset(self, dim_chunk_idx):
        if dim_chunk_idx == 0:
            return 0
        else:
            return self.get_sel_offset(dim_chunk_idx - 1) + self.get_chunk_nitems(dim_chunk_idx - 1)

    def get_chunk_ranges(self):
        for dim_chunk_idx in range(self.nchunks):
            nitems = self.get_chunk_nitems(dim_chunk_idx)
            if nitems:
                yield dim_chunk_idx


class IntegerSelection(object):

    def __init__(self, dim_sel, dim_len, dim_chunk_len):

        # TODO validate dim_sel

        self.dim_sel = dim_sel
        self.dim_len = dim_len
        self.dim_chunk_len = dim_chunk_len
        self.nchunks = int(np.ceil(self.dim_len / self.dim_chunk_len))



def normalize_dim_selection(dim_sel, dim_len, dim_chunk_len):
    """Convenience function to normalize a selection within a single axis
    of size `l`."""

    # normalize list to array
    if isinstance(dim_sel, list):
        dim_sel = np.asarray(dim_sel)

    if isinstance(dim_sel, numbers.Integral):

        # normalize type to int
        dim_sel = int(dim_sel)

        # handle wraparound
        if dim_sel < 0:
            dim_sel = dim_len + dim_sel

        # handle out of bounds
        if dim_sel >= dim_len or dim_sel < 0:
            raise IndexError('index out of bounds: %s' % dim_sel)

        return dim_sel

    elif isinstance(dim_sel, slice):

        # handle slice with step
        if dim_sel.step is not None and dim_sel.step != 1:
            raise NotImplementedError('slice with step not implemented')

        # handle slice with None bound
        start = 0 if dim_sel.start is None else dim_sel.start
        stop = dim_len if dim_sel.stop is None else dim_sel.stop

        # handle wraparound
        if start < 0:
            start = dim_len + start
        if stop < 0:
            stop = dim_len + stop

        # handle zero-length axis
        if start == stop == dim_len == 0:
            return slice(0, 0)

        # handle out of bounds
        if start < 0:
            raise IndexError('start index out of bounds: %s' % dim_sel.start)
        if stop < 0:
            raise IndexError('stop index out of bounds: %s' % dim_sel.stop)
        if start >= dim_len:
            raise IndexError('start index out of bounds: %ss' % dim_sel.start)
        if stop > dim_len:
            stop = dim_len
        if stop < start:
            stop = start

        return slice(start, stop)

    elif hasattr(dim_sel, 'dtype') and hasattr(dim_sel, 'shape'):

        if dim_sel.dtype == bool:
            return BooleanSelection(dim_sel, dim_len, dim_chunk_len)

        else:
            raise IndexError('TODO')

    else:
        raise TypeError('unsupported index item type: %r' % dim_sel)


# noinspection PyTypeChecker
def normalize_array_selection(selection, shape, chunks):
    """Convenience function to normalize a selection within an array with
    the given `shape`."""

    # ensure tuple
    if not isinstance(selection, tuple):
        selection = (selection,)

    # handle ellipsis
    n_ellipsis = sum(1 for i in selection if i is Ellipsis)
    if n_ellipsis > 1:
        raise IndexError("an index can only have a single ellipsis ('...')")
    elif n_ellipsis == 1:
        n_items_l = selection.index(Ellipsis)  # items to left of ellipsis
        n_items_r = len(selection) - (n_items_l + 1)  # items to right of ellipsis
        n_items = len(selection) - 1  # all non-ellipsis items
        if n_items >= len(shape):
            # ellipsis does nothing, just remove it
            selection = tuple(i for i in selection if i != Ellipsis)
        else:
            # replace ellipsis with as many slices are needed for number of dims
            new_item = selection[:n_items_l] + ((slice(None),) * (len(shape) - n_items))
            if n_items_r:
                new_item += selection[-n_items_r:]
            selection = new_item

    # check dimensionality
    if len(selection) > len(shape):
        raise IndexError('too many indices for array')

    # determine start and stop indices for all axes
    selection = tuple(normalize_dim_selection(i, l, c) for i, l, c in zip(selection, shape, chunks))

    # fill out selection if not completely specified
    if len(selection) < len(shape):
        selection += tuple(slice(0, l) for l in shape[len(selection):])

    return selection


def get_chunks_for_selection(selection, chunks):
    """Convenience function to find chunks overlapping an array selection. N.B.,
    assumes selection has already been normalized."""

    # indices of chunks overlapping the selection
    chunk_ranges = []

    # shape of the selection
    sel_shape = []

    # iterate over dimensions of the array
    for dim_sel, dim_chunk_len in zip(selection, chunks):

        # dim_sel: selection for current dimension
        # dim_chunk_len: length of chunk along current dimension

        dim_sel_len = None

        if isinstance(dim_sel, int):

            # dim selection is an integer, i.e., single item, so only need single chunk index for
            # this dimension
            dim_chunk_range = [dim_sel//dim_chunk_len]

        elif isinstance(dim_sel, slice):

            # dim selection is a slice, need range of chunk indices including start and stop of
            # selection
            dim_chunk_from = dim_sel.start//dim_chunk_len
            dim_chunk_to = int(np.ceil(dim_sel.stop/dim_chunk_len))
            dim_chunk_range = range(dim_chunk_from, dim_chunk_to)
            dim_sel_len = dim_sel.stop - dim_sel.start

        elif isinstance(dim_sel, BooleanSelection):

            # dim selection is a boolean array, delegate this to the BooleanSelection class
            dim_chunk_range = dim_sel.get_chunk_ranges()
            dim_sel_len = dim_sel.get_nitems()

        else:
            raise RuntimeError('unexpected selection type')

        chunk_ranges.append(dim_chunk_range)
        if dim_sel_len is not None:
            sel_shape.append(dim_sel_len)

    return chunk_ranges, tuple(sel_shape)


def normalize_resize_args(old_shape, *args):

    # normalize new shape argument
    if len(args) == 1:
        new_shape = args[0]
    else:
        new_shape = args
    if isinstance(new_shape, int):
        new_shape = (new_shape,)
    else:
        new_shape = tuple(new_shape)
    if len(new_shape) != len(old_shape):
        raise ValueError('new shape must have same number of dimensions')

    # handle None in new_shape
    new_shape = tuple(s if n is None else int(n)
                      for s, n in zip(old_shape, new_shape))

    return new_shape


def human_readable_size(size):
    if size < 2**10:
        return '%s' % size
    elif size < 2**20:
        return '%.1fK' % (size / float(2**10))
    elif size < 2**30:
        return '%.1fM' % (size / float(2**20))
    elif size < 2**40:
        return '%.1fG' % (size / float(2**30))
    elif size < 2**50:
        return '%.1fT' % (size / float(2**40))
    else:
        return '%.1fP' % (size / float(2**50))


def normalize_order(order):
    order = str(order).upper()
    if order not in ['C', 'F']:
        raise ValueError("order must be either 'C' or 'F', found: %r" % order)
    return order


def normalize_storage_path(path):

    # handle bytes
    if not PY2 and isinstance(path, bytes):  # pragma: py2 no cover
        path = str(path, 'ascii')

    # ensure str
    if path is not None and not isinstance(path, str):
        path = str(path)

    if path:

        # convert backslash to forward slash
        path = path.replace('\\', '/')

        # ensure no leading slash
        while len(path) > 0 and path[0] == '/':
            path = path[1:]

        # ensure no trailing slash
        while len(path) > 0 and path[-1] == '/':
            path = path[:-1]

        # collapse any repeated slashes
        previous_char = None
        collapsed = ''
        for char in path:
            if char == '/' and previous_char == '/':
                pass
            else:
                collapsed += char
            previous_char = char
        path = collapsed

        # don't allow path segments with just '.' or '..'
        segments = path.split('/')
        if any([s in {'.', '..'} for s in segments]):
            raise ValueError("path containing '.' or '..' segment not allowed")

    else:
        path = ''

    return path


def buffer_size(v):
    from array import array as _stdlib_array
    if PY2 and isinstance(v, _stdlib_array):  # pragma: py3 no cover
        # special case array.array because does not support buffer
        # interface in PY2
        return v.buffer_info()[1] * v.itemsize
    else:  # pragma: py2 no cover
        v = memoryview(v)
        return reduce(operator.mul, v.shape) * v.itemsize


def info_text_report(items):
    keys = [k for k, v in items]
    max_key_len = max(len(k) for k in keys)
    report = ''
    for k, v in items:
        wrapper = TextWrapper(width=80,
                              initial_indent=k.ljust(max_key_len) + ' : ',
                              subsequent_indent=' '*max_key_len + ' : ')
        text = wrapper.fill(str(v))
        report += text + '\n'
    return report


def info_html_report(items):
    report = '<table class="zarr-info">'
    report += '<tbody>'
    for k, v in items:
        report += '<tr>' \
                  '<th style="text-align: left">%s</th>' \
                  '<td style="text-align: left">%s</td>' \
                  '</tr>' \
                  % (k, v)
    report += '</tbody>'
    report += '</table>'
    return report


class InfoReporter(object):

    def __init__(self, obj):
        self.obj = obj

    def __repr__(self):
        items = self.obj.info_items()
        return info_text_report(items)

    def _repr_html_(self):
        items = self.obj.info_items()
        return info_html_report(items)
