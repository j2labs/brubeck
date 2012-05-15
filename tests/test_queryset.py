#!/usr/bin/env python

import unittest

import brubeck
from handlers.method_handlers import simple_handler_method
from brubeck.request_handling import Brubeck, WebMessageHandler, JSONMessageHandler
from brubeck.connections import to_bytes, Request
from brubeck.request_handling import(
    cookie_encode, cookie_decode,
    cookie_is_encoded, http_response
)
from handlers.object_handlers import(
    SimpleWebHandlerObject, CookieWebHandlerObject,
    SimpleJSONHandlerObject, CookieAddWebHandlerObject,
    PrepareHookWebHandlerObject, InitializeHookWebHandlerObject
)
from fixtures import request_handler_fixtures as FIXTURES

from brubeck.autoapi import AutoAPIBase
from brubeck.queryset import DictQueryset, AbstractQueryset, RedisQueryset

from dictshield.document import Document
from dictshield.fields import StringField
from brubeck.request_handling import FourOhFourException

##TestDocument
class TestDoc(Document):
    data = StringField()
    class Meta:
        id_field = StringField

###
### Tests for ensuring that the autoapi returns good data
###
class TestQuerySetPrimitives(unittest.TestCase):
    """
    a test class for brubeck's queryset objects' core operations.
    """

    def setUp(self):
        self.queryset = AbstractQueryset()


    def create(self):
        pass

    def read(self):
        pass

    def update(self):
        pass

    def destroy(self):
       pass


class TestDictQueryset(unittest.TestCase):
    """
    a test class for brubeck's dictqueryset's operations.
    """


    def setUp(self):
        self.queryset = DictQueryset()

    def seed_reads(self):
        shields = [TestDoc(id="foo"), TestDoc(id="bar"), TestDoc(id="baz")]
        self.queryset.create_many(shields)
        return shields


    def test__create_one(self):
        shield = TestDoc(id="foo")
        status, return_shield = self.queryset.create_one(shield)
        self.assertEqual(self.queryset.MSG_CREATED, status)
        self.assertEqual(shield, return_shield)

        status, return_shield = self.queryset.create_one(shield)
        self.assertEqual(self.queryset.MSG_UPDATED, status)


    def test__create_many(self):
        shield0 = TestDoc(id="foo")
        shield1 = TestDoc(id="bar")
        shield2 = TestDoc(id="baz")
        statuses = self.queryset.create_many([shield0, shield1, shield2])
        for status, datum in statuses:
            self.assertEqual(self.queryset.MSG_CREATED, status)

        shield3 = TestDoc(id="bloop")
        statuses = self.queryset.create_many([shield0, shield3, shield2])
        status, datum = statuses[1]
        self.assertEqual(self.queryset.MSG_CREATED, status)
        status, datum = statuses[0]
        self.assertEqual(self.queryset.MSG_UPDATED, status)

    def test__read_all(self):
        shields = self.seed_reads()
        statuses = self.queryset.read_all()

        for status, datum in statuses:
            self.assertEqual(self.queryset.MSG_OK, status)

        actual = sorted([datum for trash, datum in statuses])
        expected = sorted([shield.to_python() for shield in shields])
        self.assertEqual(expected, actual)

    def test__read_one(self):
        shields = self.seed_reads()
        for shield in shields:
            status, datum = self.queryset.read_one(shield.id)
            self.assertEqual(self.queryset.MSG_OK, status)
            self.assertEqual(datum, shield.to_python())
        bad_key = 'DOESNTEXISIT'
        status, datum = self.queryset.read(bad_key)
        self.assertEqual(bad_key, datum)
        self.assertEqual(self.queryset.MSG_FAILED, status)

    def test__read_many(self):
        shields = self.seed_reads()
        expected = [shield.to_python() for shield in shields]
        responses = self.queryset.read_many([s.id for s in shields])
        for status, datum in responses:
            self.assertEqual(self.queryset.MSG_OK, status)
            self.assertTrue(datum in expected)

        bad_ids = [s.id for s in shields]
        bad_ids.append('DOESNTEXISIT')
        status, iid = self.queryset.read_many(bad_ids)[-1]
        self.assertEqual(self.queryset.MSG_FAILED, status)


    def test_update_one(self):
        shields = self.seed_reads()
        test_shield = shields[0]
        test_shield.data = "foob"
        status, datum = self.queryset.update_one(test_shield)

        self.assertEqual(self.queryset.MSG_UPDATED, status)
        self.assertEqual('foob', datum['data'])

        status, datum =  self.queryset.read_one(test_shield.id)
        self.assertEqual('foob', datum['data'])


    def test_update_many(self):
        shields = self.seed_reads()
        for shield in shields:
            shield.data = "foob"
        responses = self.queryset.update_many(shields)
        for status, datum in responses:
            self.assertEqual(self.queryset.MSG_UPDATED, status)
            self.assertEqual('foob', datum['data'])
        for status, datum in self.queryset.read_all():
            self.assertEqual('foob', datum['data'])


    def test_destroy_one(self):
        shields = self.seed_reads()
        test_shield = shields[0]
        status, datum = self.queryset.destroy_one(test_shield.id)
        self.assertEqual(self.queryset.MSG_UPDATED, status)

        status, datum = self.queryset.read_one(test_shield.id)
        self.assertEqual(test_shield.id, datum)
        self.assertEqual(self.queryset.MSG_FAILED, status)


    def test_destroy_many(self):
        shields = self.seed_reads()
        shield_to_keep = shields.pop()
        responses = self.queryset.destroy_many([shield.id for shield in shields])
        for status, datum in responses:
            self.assertEqual(self.queryset.MSG_UPDATED, status)

        responses = self.queryset.read_many([shield.id for shield in shields])
        for status, datum in responses:
            self.assertEqual(self.queryset.MSG_FAILED, status)

        status, datum = self.queryset.read_one(shield_to_keep.id)
        self.assertEqual(self.queryset.MSG_OK, status)
        self.assertEqual(shield_to_keep.to_python(), datum)


class TestRedisQueryset(unittest.TestCase):
    """
    a test class for brubeck's RedisQueryset's operations.
    """


    def setUp(self):
        import redis
        redis_connection = redis.StrictRedis(host='localhost', port=6379, db=0)
        self.queryset = RedisQueryset(db_conn=redis_connection)

    def seed_reads(self):
        shields = [TestDoc(id="foo"), TestDoc(id="bar"), TestDoc(id="baz")]
        self.queryset.create_many(shields)
        return shields


    def test__create_one(self):
        # TODO: - fix test
        # Test will fail, unless the value associated with 
        # 'id': 'foo' is deleted. Normally, during this test an object with id='foo'
        # exists- test may need to be fixed. If the object "foo" exists
        # the first operation will return self.queryset.MSG_UPDATED instead
        # of self.queryset.MSG_FAILED
        import redis
        redis_connection = redis.StrictRedis(host='localhost', port=6379, db=0)
        redis_connection.delete('id')
        
        shield = TestDoc(id="foo")
        status, return_shield = self.queryset.create_one(shield)
        self.assertEqual(self.queryset.MSG_CREATED, status)
        self.assertEqual(shield, return_shield)

        status, return_shield = self.queryset.create_one(shield)
        self.assertEqual(self.queryset.MSG_UPDATED, status)


    def test__create_many(self):
        shield0 = TestDoc(id="foo")
        shield1 = TestDoc(id="bar")
        shield2 = TestDoc(id="baz")
        statuses = self.queryset.create_many([shield0, shield1, shield2])
        for status, datum in statuses:
            self.assertEqual(self.queryset.MSG_CREATED, status)

        shield3 = TestDoc(id="bloop")
        statuses = self.queryset.create_many([shield0, shield3, shield2])
        status, datum = statuses[1]
        self.assertEqual(self.queryset.MSG_CREATED, status)
        status, datum = statuses[0]
        self.assertEqual(self.queryset.MSG_UPDATED, status)

    def test__read_all(self):
        shields = self.seed_reads()
        statuses = self.queryset.read_all()

        for status, datum in statuses:
            self.assertEqual(self.queryset.MSG_OK, status)

        actual = sorted([datum for trash, datum in statuses])
        expected = sorted([shield.to_python() for shield in shields])
        self.assertEqual(expected, actual)

    def test__read_one(self):
        shields = self.seed_reads()
        for shield in shields:
            status, datum = self.queryset.read_one(shield.id)
            self.assertEqual(self.queryset.MSG_OK, status)
            self.assertEqual(datum, shield.to_python())
        bad_key = 'DOESNTEXIST'
        status, datum = self.queryset.read(bad_key)
        self.assertEqual(bad_key, datum)
        self.assertEqual(self.queryset.MSG_FAILED, status)

    def test__read_many(self):
        shields = self.seed_reads()
        expected = [shield.to_python() for shield in shields]
        responses = self.queryset.read_many([s.id for s in shields])
        for status, datum in responses:
            self.assertEqual(self.queryset.MSG_OK, status)
            self.assertTrue(datum in expected)

        bad_ids = [s.id for s in shields]
        bad_ids.append('DOESNTEXIST')
        status, iid = self.queryset.read_many(bad_ids)[-1]
        self.assertEqual(self.queryset.MSG_FAILED, status)


    def test_update_one(self):
        shields = self.seed_reads()
        test_shield = shields[0]
        test_shield.data = "foob"
        status, datum = self.queryset.update_one(test_shield)

        self.assertEqual(self.queryset.MSG_UPDATED, status)
        self.assertEqual('foob', datum['data'])

        status, datum =  self.queryset.read_one(test_shield.id)
        self.assertEqual('foob', datum['data'])


    def test_update_many(self):
        shields = self.seed_reads()
        for shield in shields:
            shield.data = "foob"
        responses = self.queryset.update_many(shields)
        for status, datum in responses:
            self.assertEqual(self.queryset.MSG_UPDATED, status)
            self.assertEqual('foob', datum['data'])
        for status, datum in self.queryset.read_all():
            self.assertEqual('foob', datum['data'])


    def test_destroy_one(self):
        shields = self.seed_reads()
        test_shield = shields[0]
        status, datum = self.queryset.destroy_one(test_shield.id)
        self.assertEqual(self.queryset.MSG_UPDATED, status)

        status, datum = self.queryset.read_one(test_shield.id)
        self.assertEqual(test_shield.id, datum)
        self.assertEqual(self.queryset.MSG_FAILED, status)


    def test_destroy_many(self):
        shields = self.seed_reads()
        shield_to_keep = shields.pop()
        responses = self.queryset.destroy_many([shield.id for shield in shields])
        for status, datum in responses:
            self.assertEqual(self.queryset.MSG_UPDATED, status)

        responses = self.queryset.read_many([shield.id for shield in shields])
        for status, datum in responses:
            self.assertEqual(self.queryset.MSG_FAILED, status)

        status, datum = self.queryset.read_one(shield_to_keep.id)
        self.assertEqual(self.queryset.MSG_OK, status)
        self.assertEqual(shield_to_keep.to_python(), datum)


##
## This will run our tests
##
if __name__ == '__main__':
    unittest.main()
