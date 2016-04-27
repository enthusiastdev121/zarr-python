# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division
import json
from collections import MutableMapping


class Attributes(MutableMapping):

    def __init__(self, store, key='attrs', readonly=False):
        if key not in store:
            store[key] = json.dumps(dict())
        self.store = store
        self.key = key
        self.readonly = readonly

    def __contains__(self, x):
        return x in self.asdict()

    def __getitem__(self, item):
        return self.asdict()[item]

    def put(self, d):

        # guard conditions
        if self.readonly:
            raise PermissionError('attributes are read-only')

        s = json.dumps(d, indent=4, sort_keys=True, ensure_ascii=True)
        self.store[self.key] = s.encode('ascii')

    def __setitem__(self, key, value):

        # guard conditions
        if self.readonly:
            raise PermissionError('attributes are read-only')

        # load existing data
        d = self.asdict()

        # set key value
        d[key] = value

        # put modified data
        self.put(d)

    def __delitem__(self, key):

        # guard conditions
        if self.readonly:
            raise PermissionError('mapping is read-only')

        # load existing data
        d = self.asdict()

        # delete key value
        del d[key]

        # put modified data
        self.put(d)

    def asdict(self):
        return json.loads(str(self.store[self.key], 'ascii'))

    def update(self, *args, **kwargs):
        # override to provide update in a single write

        # guard conditions
        if self.readonly:
            raise PermissionError('mapping is read-only')

        # load existing data
        d = self.asdict()

        # update
        d.update(*args, **kwargs)

        # put modified data
        self.put(d)

    def __iter__(self):
        return iter(self.asdict())

    def __len__(self):
        return len(self.asdict())

    def keys(self):
        return self.asdict().keys()

    def values(self):
        return self.asdict().values()

    def items(self):
        return self.asdict().items()


class SynchronizedAttributes(Attributes):

    def __init__(self, store, synchronizer, key='attrs', readonly=False):
        super(SynchronizedAttributes, self).__init__(store, key=key,
                                                     readonly=readonly)
        self.synchronizer = synchronizer

    def __setitem__(self, key, value):
        with self.synchronizer.lock_attrs():
            super(SynchronizedAttributes, self).__setitem__(key, value)

    def __delitem__(self, key):
        with self.synchronizer.lock_attrs():
            super(SynchronizedAttributes, self).__delitem__(key)

    def update(self, *args, **kwargs):
        with self.synchronizer.lock_attrs():
            super(SynchronizedAttributes, self).update(*args, **kwargs)
