# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division
import json
import unittest
import collections


from nose.tools import eq_ as eq, assert_raises


from zarr.attrs import Attributes
from zarr.compat import binary_type, text_type
from zarr.errors import PermissionError


class CountingDict(collections.MutableMapping):

    def __init__(self):
        self.wrapped = dict()
        self.counter = collections.Counter()

    def __len__(self):
        return len(self.wrapped)

    def __iter__(self):
        return iter(self.wrapped)

    def __contains__(self, item):
        return item in self.wrapped

    def __getitem__(self, item):
        self.counter['__getitem__', item] += 1
        return self.wrapped[item]

    def __setitem__(self, key, value):
        self.counter['__setitem__', key] += 1
        self.wrapped[key] = value

    def __delitem__(self, key):
        self.counter['__delitem__', key] += 1
        del self.wrapped[key]


class TestAttributes(unittest.TestCase):

    def init_attributes(self, store, read_only=False, cache=True):
        return Attributes(store, key='attrs', read_only=read_only, cache=cache)

    def test_storage(self):

        store = dict()
        a = Attributes(store=store, key='attrs')
        assert 'foo' not in a
        assert 'bar' not in a
        eq(dict(), a.asdict())

        a['foo'] = 'bar'
        a['baz'] = 42
        assert 'attrs' in store
        assert isinstance(store['attrs'], binary_type)
        d = json.loads(text_type(store['attrs'], 'ascii'))
        eq(dict(foo='bar', baz=42), d)

    def test_get_set_del_contains(self):

        a = self.init_attributes(dict())
        assert 'foo' not in a
        a['foo'] = 'bar'
        a['baz'] = 42
        assert 'foo' in a
        assert 'baz' in a
        eq('bar', a['foo'])
        eq(42, a['baz'])
        del a['foo']
        assert 'foo' not in a
        with assert_raises(KeyError):
            a['foo']

    def test_update(self):

        a = self.init_attributes(dict())
        assert 'foo' not in a
        assert 'baz' not in a
        a.update(foo='bar', baz=42)
        eq(a['foo'], 'bar')
        eq(a['baz'], 42)

    def test_iterators(self):

        a = self.init_attributes(dict())
        eq(0, len(a))
        eq(set(), set(a))
        eq(set(), set(a.keys()))
        eq(set(), set(a.values()))
        eq(set(), set(a.items()))

        a['foo'] = 'bar'
        a['baz'] = 42

        eq(2, len(a))
        eq({'foo', 'baz'}, set(a))
        eq({'foo', 'baz'}, set(a.keys()))
        eq({'bar', 42}, set(a.values()))
        eq({('foo', 'bar'), ('baz', 42)}, set(a.items()))

    def test_read_only(self):
        store = dict()
        a = self.init_attributes(store, read_only=True)
        store['attrs'] = json.dumps(dict(foo='bar', baz=42)).encode('ascii')
        eq(a['foo'], 'bar')
        eq(a['baz'], 42)
        with assert_raises(PermissionError):
            a['foo'] = 'quux'
        with assert_raises(PermissionError):
            del a['foo']
        with assert_raises(PermissionError):
            a.update(foo='quux')

    def test_key_completions(self):
        a = self.init_attributes(dict())
        d = a._ipython_key_completions_()
        assert 'foo' not in d
        assert '123' not in d
        assert 'baz' not in d
        assert 'asdf;' not in d
        a['foo'] = 42
        a['123'] = 4.2
        a['asdf;'] = 'ghjkl;'
        d = a._ipython_key_completions_()
        assert 'foo' in d
        assert '123' in d
        assert 'asdf;' in d
        assert 'baz' not in d

    def test_caching_on(self):
        # caching is turned on by default
        store = CountingDict()
        eq(0, store.counter['__getitem__', 'attrs'])
        eq(0, store.counter['__setitem__', 'attrs'])
        store['attrs'] = json.dumps(dict(foo='xxx', bar=42)).encode('ascii')
        eq(0, store.counter['__getitem__', 'attrs'])
        eq(1, store.counter['__setitem__', 'attrs'])
        a = self.init_attributes(store)
        eq(a['foo'], 'xxx')
        eq(1, store.counter['__getitem__', 'attrs'])
        eq(a['bar'], 42)
        eq(1, store.counter['__getitem__', 'attrs'])
        eq(a['foo'], 'xxx')
        eq(1, store.counter['__getitem__', 'attrs'])
        a['foo'] = 'yyy'
        eq(2, store.counter['__getitem__', 'attrs'])
        eq(2, store.counter['__setitem__', 'attrs'])
        eq(a['foo'], 'yyy')
        eq(2, store.counter['__getitem__', 'attrs'])
        eq(2, store.counter['__setitem__', 'attrs'])
        a.update(foo='zzz', bar=84)
        eq(3, store.counter['__getitem__', 'attrs'])
        eq(3, store.counter['__setitem__', 'attrs'])
        eq(a['foo'], 'zzz')
        eq(a['bar'], 84)
        eq(3, store.counter['__getitem__', 'attrs'])
        eq(3, store.counter['__setitem__', 'attrs'])
        assert 'foo' in a
        eq(3, store.counter['__getitem__', 'attrs'])
        eq(3, store.counter['__setitem__', 'attrs'])
        assert 'spam' not in a
        eq(3, store.counter['__getitem__', 'attrs'])
        eq(3, store.counter['__setitem__', 'attrs'])

    def test_caching_off(self):
        store = CountingDict()
        eq(0, store.counter['__getitem__', 'attrs'])
        eq(0, store.counter['__setitem__', 'attrs'])
        store['attrs'] = json.dumps(dict(foo='xxx', bar=42)).encode('ascii')
        eq(0, store.counter['__getitem__', 'attrs'])
        eq(1, store.counter['__setitem__', 'attrs'])
        a = self.init_attributes(store, cache=False)
        eq(a['foo'], 'xxx')
        eq(1, store.counter['__getitem__', 'attrs'])
        eq(a['bar'], 42)
        eq(2, store.counter['__getitem__', 'attrs'])
        eq(a['foo'], 'xxx')
        eq(3, store.counter['__getitem__', 'attrs'])
        a['foo'] = 'yyy'
        eq(4, store.counter['__getitem__', 'attrs'])
        eq(2, store.counter['__setitem__', 'attrs'])
        eq(a['foo'], 'yyy')
        eq(5, store.counter['__getitem__', 'attrs'])
        eq(2, store.counter['__setitem__', 'attrs'])
        a.update(foo='zzz', bar=84)
        eq(6, store.counter['__getitem__', 'attrs'])
        eq(3, store.counter['__setitem__', 'attrs'])
        eq(a['foo'], 'zzz')
        eq(a['bar'], 84)
        eq(8, store.counter['__getitem__', 'attrs'])
        eq(3, store.counter['__setitem__', 'attrs'])
        assert 'foo' in a
        eq(9, store.counter['__getitem__', 'attrs'])
        eq(3, store.counter['__setitem__', 'attrs'])
        assert 'spam' not in a
        eq(10, store.counter['__getitem__', 'attrs'])
        eq(3, store.counter['__setitem__', 'attrs'])
