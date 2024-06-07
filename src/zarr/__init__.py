from zarr._version import version as __version__
from zarr.api.synchronous import (
    array,
    consolidate_metadata,
    copy,
    copy_all,
    copy_store,
    create,
    empty,
    empty_like,
    full,
    full_like,
    group,
    load,
    ones,
    ones_like,
    open,
    open_array,
    open_consolidated,
    open_group,
    open_like,
    save,
    save_array,
    save_group,
    tree,
    zeros,
    zeros_like,
)
from zarr.array import Array, AsyncArray
from zarr.config import config
from zarr.group import AsyncGroup, Group

# in case setuptools scm screw up and find version to be 0.0.0
assert not __version__.startswith("0.0.0")

__all__ = [
    "__version__",
    "config",
    "Array",
    "AsyncArray",
    "Group",
    "AsyncGroup",
    "tree",
    "array",
    "consolidate_metadata",
    "copy",
    "copy_all",
    "copy_store",
    "create",
    "empty",
    "empty_like",
    "full",
    "full_like",
    "group",
    "load",
    "ones",
    "ones_like",
    "open",
    "open_array",
    "open_consolidated",
    "open_group",
    "open_like",
    "save",
    "save_array",
    "save_group",
    "zeros",
    "zeros_like",
]
