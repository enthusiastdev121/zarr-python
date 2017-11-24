Storage (``zarr.storage``)
==========================
.. automodule:: zarr.storage

.. autoclass:: DictStore
.. autoclass:: DirectoryStore
.. autoclass:: TempStore
.. autoclass:: NestedDirectoryStore
.. autoclass:: ZipStore

    .. automethod:: close
    .. automethod:: flush

.. autoclass:: DBMStore

    .. automethod:: close
    .. automethod:: flush

.. autoclass:: LMDBStore

    .. automethod:: close
    .. automethod:: flush

.. autofunction:: init_array
.. autofunction:: init_group
.. autofunction:: migrate_1to2
