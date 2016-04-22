# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division
import multiprocessing
import atexit


from zarr.core import Array, SynchronizedArray, set_blosc_options
from zarr.store import ArrayStore, MemoryStore, DirectoryStore
from zarr.sync import ThreadSynchronizer, ProcessSynchronizer
from zarr.create import array, empty, zeros, ones, full, open, empty_like, \
    zeros_like, ones_like, full_like, open_like
from zarr import blosc


ncores = multiprocessing.cpu_count()
blosc.init()
# diminishing returns beyond 4 threads?
set_blosc_options(use_context=False, nthreads=min(4, ncores))
atexit.register(blosc.destroy)
