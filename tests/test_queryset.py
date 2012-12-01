#!/usr/bin/env python

import unittest

import mock

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


class TestRedisQueryset(TestQuerySetPrimitives):
    """
    Test RedisQueryset operations.
    """
    def setUp(self):
        pass

    def seed_reads(self):
        shields = [TestDoc(id="foo"), TestDoc(id="bar"), TestDoc(id="baz")]
        return shields

    def test__create_one(self):
        with mock.patch('redis.StrictRedis') as patchedRedis:
            redis_connection = patchedRedis(host='localhost', port=6379, db=0)
            queryset = RedisQueryset(db_conn=redis_connection)
            
            shield = TestDoc(id="foo")
            queryset.create_one(shield)
            
            name, args, kwargs = redis_connection.mock_calls[0]
            self.assertEqual(name, 'hset')
            self.assertEqual(args, (queryset.api_id, 'foo', '{"_types": ["TestDoc"], "id": "foo", "_cls": "TestDoc"}'))
            
    def test__create_many(self):
        with mock.patch('redis.StrictRedis') as patchedRedis:
            redis_connection = patchedRedis(host='localhost', port=6379, db=0)
            queryset = RedisQueryset(db_conn=redis_connection)
            queryset.create_many(self.seed_reads())
            expected = [
                ('pipeline', (), {}),
                ('pipeline().hset', (queryset.api_id, 'foo', '{"_types": ["TestDoc"], "id": "foo", "_cls": "TestDoc"}'), {}),
                ('pipeline().hset', (queryset.api_id, 'bar', '{"_types": ["TestDoc"], "id": "bar", "_cls": "TestDoc"}'), {}),
                ('pipeline().hset', (queryset.api_id, 'baz', '{"_types": ["TestDoc"], "id": "baz", "_cls": "TestDoc"}'), {}),
                ('pipeline().execute', (), {}),
                ('pipeline().execute().__iter__', (), {}),
                ('pipeline().reset', (), {})
                ]
            for call in zip(expected, redis_connection.mock_calls):
                self.assertEqual(call[0], call[1])

    def test__read_all(self):
        with mock.patch('redis.StrictRedis') as patchedRedis:
            redis_connection = patchedRedis(host='localhost', port=6379, db=0)
            queryset = RedisQueryset(db_conn=redis_connection)
            statuses = queryset.read_all()
            
            name, args, kwargs = redis_connection.mock_calls[0]
            self.assertEqual(name, 'hvals')
            self.assertEqual(args, (queryset.api_id,))
            
            name, args, kwargs = redis_connection.mock_calls[1]
            self.assertEqual(name, 'hvals().__iter__')
            self.assertEqual(args, ())

    def test__read_one(self):
        for _id in ['foo', 'bar', 'baz']:
            with mock.patch('redis.StrictRedis') as patchedRedis:
                instance = patchedRedis.return_value
                instance.hget.return_value = '{"called": "hget"}'
                redis_connection = patchedRedis(host='localhost', port=6379, db=0)
                queryset = RedisQueryset(db_conn=redis_connection)

                msg, result = queryset.read_one(_id)
                assert (RedisQueryset.MSG_OK, {'called': 'hget'}) == (msg, result)

                name, args, kwargs = redis_connection.mock_calls[0]
                self.assertEqual(name, 'hget')
                self.assertEqual(args, (queryset.api_id, _id))
                self.assertEqual(kwargs, {})
                
    def test__read_many(self):
        with mock.patch('redis.StrictRedis') as patchedRedis:
            redis_connection = patchedRedis(host='localhost', port=6379, db=0)
            queryset = RedisQueryset(db_conn=redis_connection)
            queryset.read_many(['foo', 'bar', 'baz', 'laser', 'beams'])
            expected = [('pipeline', (), {}),
                        ('pipeline().hget', (queryset.api_id, 'foo'), {}),
                        ('pipeline().hget', (queryset.api_id, 'bar'), {}),
                        ('pipeline().hget', (queryset.api_id, 'baz'), {}),
                        ('pipeline().hget', (queryset.api_id, 'laser'), {}),
                        ('pipeline().hget', (queryset.api_id, 'beams'), {}),
                        ('pipeline().execute', (), {}),
                        ('pipeline().reset', (), {}),
                        ('pipeline().execute().__iter__', (), {}),
                        ('pipeline().execute().__iter__', (), {}),
                        ('pipeline().execute().__len__', (), {}),
                        ]
            for call in zip(expected, redis_connection.mock_calls):
                assert call[0] == call[1]

    def test_update_one(self):
        with mock.patch('redis.StrictRedis') as patchedRedis:
            instance = patchedRedis.return_value
            redis_connection = patchedRedis(host='localhost', port=6379, db=0)
            queryset = RedisQueryset(db_conn=redis_connection)

            original = mock.Mock()
            doc_instance = original.return_value
            doc_instance.id = 'foo'
            doc_instance.to_json.return_value = '{"to": "json"}'

            queryset.update_one(doc_instance)

            expected = ('hset', ('id', 'foo', '{"to": "json"}'), {})

            self.assertEqual(expected, redis_connection.mock_calls[0])


    def test_update_many(self):
        with mock.patch('redis.StrictRedis') as patchedRedis:
            redis_connection = patchedRedis(host='localhost', port=6379, db=0)
            queryset = RedisQueryset(db_conn=redis_connection)
            queryset.update_many(self.seed_reads())
            expected = [
                ('pipeline', (), {}),
                ('pipeline().hset', (queryset.api_id, 'foo', '{"_types": ["TestDoc"], "id": "foo", "_cls": "TestDoc"}'), {}),
                ('pipeline().hset', (queryset.api_id, 'bar', '{"_types": ["TestDoc"], "id": "bar", "_cls": "TestDoc"}'), {}),
                ('pipeline().hset', (queryset.api_id, 'baz', '{"_types": ["TestDoc"], "id": "baz", "_cls": "TestDoc"}'), {}),
                ('pipeline().execute', (), {}),
                ('pipeline().reset', (), {}),
                ('pipeline().execute().__iter__', (), {}),
                ]

            for call in zip(expected, redis_connection.mock_calls):
                self.assertEqual(call[0], call[1])

    def test_destroy_one(self):
        with mock.patch('redis.StrictRedis') as patchedRedis:
            instance = patchedRedis.return_value
            instance.pipeline = mock.Mock()
            pipe_instance = instance.pipeline.return_value
            pipe_instance.execute.return_value = ('{"success": "hget"}', 1)

            redis_connection = patchedRedis(host='localhost', port=6379, db=0)
            queryset = RedisQueryset(db_conn=redis_connection)
            queryset.destroy_one('bar')

            expected = [
                ('pipeline', (), {}),
                ('pipeline().hget', ('id', 'bar'), {}),
                ('pipeline().hdel', ('id', 'bar'), {}),
                ('pipeline().execute', (), {})
                ]
            for call in zip(expected, redis_connection.mock_calls):
                self.assertEqual(call[0], call[1])

    def test_destroy_many(self):
        with mock.patch('redis.StrictRedis') as patchedRedis:
            instance = patchedRedis.return_value
            instance.pipeline = mock.Mock()
            pipe_instance = instance.pipeline.return_value
            shields = self.seed_reads()
            json_shields = [shield.to_json() for shield in shields]
            results = json_shields
            pipe_instance.execute.return_value = results
            
            redis_connection = patchedRedis(host='localhost', port=6379, db=0)
            
            queryset = RedisQueryset(db_conn=redis_connection)

            queryset.destroy_many([shield.id for shield in shields])

            expected = [('pipeline', (), {}),
                        ('pipeline().hget', (queryset.api_id, 'foo'), {}),
                        ('pipeline().hget', (queryset.api_id, 'bar'), {}),
                        ('pipeline().hget', (queryset.api_id, 'baz'), {}),
                        ('pipeline().execute', (), {}),
                        ('pipeline().hdel', (queryset.api_id, 'foo'), {}),
                        ('pipeline().hdel', (queryset.api_id, 'bar'), {}),
                        ('pipeline().hdel', (queryset.api_id, 'baz'), {}),
                        ('pipeline().execute', (), {}),
                        ('pipeline().reset', (), {})
                        ]
            for call in zip(expected, redis_connection.mock_calls):
                self.assertEqual(call[0], call[1])

##
## This will run our tests
##
if __name__ == '__main__':
    unittest.main()
