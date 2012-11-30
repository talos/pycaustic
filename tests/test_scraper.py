#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import json
sys.path.insert(0, os.path.abspath('..'))

from helpers import unittest
from pycaustic import Scraper
from pycaustic.errors import InvalidInstructionError

FILE_PATH = os.path.abspath(__file__)

class TestSetup(object):

    def setUp(self):
        pass


class StubMixin():

    def mockRequest(self, url, method='get', status=200, headers={},
                        content=''):
        """
        Mock an HTTP request.
        """
        pass


class TestScraper(TestSetup, StubMixin, unittest.TestCase):

    def test_simple_find(self):
        """
        Test scraping data from predefined input.
        """
        instruction = {
            'find': 'foobar',
        }
        resp = Scraper().scrape(instruction, input="foobar baz boo")

        self.assertEquals('found', resp.status)
        results = resp.results

        # Should have one result
        self.assertEquals(1, len(results))
        result = results[0]

        # It should have the value from regex and no children
        self.assertEquals('foobar', result.value)
        self.assertIsNone(result.children)

    def test_filesystem_json(self):
        """
        Test loading in some JSON
        """
        instruction = 'fixtures/find-foobar.json'
        resp = Scraper().scrape(instruction, input="foobar baz boo",
                                uri= FILE_PATH)

        self.assertEquals('found', resp.status)
        self.assertEquals({
            'value': 'foobar'
        }, resp.results[0].as_dict())

    def test_filesystem_ref(self):
        """
        Test loading in some JSON by reference in extends
        """
        instruction = 'fixtures/find-foobar-by-extension.json'
        resp = Scraper().scrape(instruction, input="foobar baz boo",
                                uri= FILE_PATH)

        self.assertEquals('found', resp.status)
        self.assertEquals({
            'value': 'foobar'
        }, resp.results[0].as_dict())

    def test_object_extends(self):
        """
        We should be able to get a valid scraper using extends.
        """
        instruction = {
            "extends": {
                "find": r"foo\w+"
            },
            "match": 1
        }
        resp = Scraper().scrape(instruction, input="foobar foobaz")

        # results should only be the second 'foo'
        self.assertEquals('found', resp.status)
        self.assertEquals([{
            'value': 'foobaz'
        }], [r.as_dict() for r in resp.results])

    def test_array_extends(self):
        """
        We should be able to get a valid scraper using an array of extends
        objects.
        """
        instruction = {
            "extends": [{
                "find": r"foo\w+"
            },{
                "match": 1
            }]
        }
        resp = Scraper().scrape(instruction, input="foobar foobaz")

        # results should only be the second 'foo'
        self.assertEquals('found', resp.status)
        self.assertEquals([{
            'value': 'foobaz'
        }], [r.as_dict() for r in resp.results])

    def test_object_extends_update(self):
        """
        We should be able to use extends to update certain keys (posts!) in the
        original.
        """
        resp = Scraper().scrape({
            'load': 'http://httpbin.org/post',
            'posts': {
                'roses': 'red'
            },
            'extends': {
                'posts': {
                    'violets': 'blue'
                }
            }
        }, force=True)
        self.assertEquals('loaded', resp.status)
        bin_content = json.loads(resp.results[0].value)
        self.assertEquals({
            'roses': 'red',
            'violets': 'blue'
        }, bin_content['form'])

    def xtest_simple_google_request(self):
        """
        Test a very straightforward request to Google to look for "I'm feeling
        lucky".
        """
        instruction = {
            "load"  : "http://www.google.com",
            "then" : {
                "find" : "Feeling\\s[\\w]*",
                "name" : "Feeling?",
                "match": 0
            }
        }
        resp = Scraper().scrape(instruction, force=True)

        # Outer level
        self.assertEquals('loaded', resp.status)

        # Should have one result from page load
        results = resp.results
        self.assertEquals(1, len(results))
        result = results[0]

        # This result should have one child
        children = result.children
        self.assertEquals(1, len(children))
        child = children[0]

        # This child should have been successful with the name specified in
        # instruction
        self.assertEquals('found', child.status)
        self.assertEquals('Feeling?', child.name)

        # The child should have one result
        results = child.results
        self.assertEquals(1, len(results))
        result = results[0]

        # Whose value should be the word after "Feeling"
        self.assertEquals('Feeling Lucky', result.value)

        # And which has no children
        self.assertIsNone(result.children)

    def test_then_reference_string(self):
        """
        Test that the proper URI is maintained for resolving "then"
        """
        resp = Scraper().scrape('fixtures/then-link.json',
                                uri=FILE_PATH,
                               input="foobaz foobar")

        self.assertEquals(resp.status, 'found')
        self.assertEquals('foobar', resp.results[1].value)
        self.assertEquals('foobar', resp.results[1].children[0].results[0].value)

    def test_then_reference_list(self):
        """
        Test that the proper URI is maintained for resolving "then" in
        a list
        """
        resp = Scraper().scrape('fixtures/then-links.json',
                                uri=FILE_PATH,
                               input="foobaz foobar")

        self.assertEquals(resp.status, 'found')
        self.assertEquals('foobar', resp.results[1].value)
        self.assertEquals('foobar', resp.results[1].children[0].results[0].value)
        self.assertEquals('foobar', resp.results[1].children[1].results[0].value)

    def test_nonexistent_file(self):
        """
        Test that an InvalidInstructionError is thrown for unknown files.
        """
        with self.assertRaises(InvalidInstructionError):
            Scraper().scrape('/does/not/exist')

    def test_nested_files(self):
        """
        Each URI should be resolved relative to the current URL.
        """
        resp = Scraper().scrape('fixtures/nested.json',
                                uri=FILE_PATH,
                               input="there are some russian dolls")

        self.assertEquals(resp.status, 'found')
        self.assertEquals('some russian dolls', resp.results[0].value)
        self.assertEquals('russian dolls', resp.results[0].children[0].results[0].value)
        self.assertEquals('dolls', resp.results[0].children[0].results[0].children[0].results[0].value)

    def test_flattened_values_all_one_to_one(self):
        """
        Flattened values
        """
        resp = Scraper().scrape({
            "find": "^.*$",
            "name": "everything",
            "match": 0,
            "then": [{
                'name': 'roses',
                'find': 'red'
            }, {
                'name': 'violets',
                'find': 'blue'
            }]
        }, input='red blue')
        self.assertEquals({
            'everything': 'red blue',
            'roses': 'red',
            'violets': 'blue'
        }, resp.flattened_values)

    def test_flattened_values_with_one_to_many(self):
        """
        Flattened values
        """
        resp = Scraper().scrape({
            "find": "^.*$",
            "name": "everything",
            "match": 0,
            "then": [{
                'name': 'roses',
                'find': 'red'
            }, {
                'name': 'violets',
                'find': 'blue'
            }]
        }, input='red blue blue')
        self.assertEquals({
            'everything': 'red blue blue',
            'roses': 'red',
            'violets': [{'violets': 'blue' },
                        {'violets': 'blue' } ]
        }, resp.flattened_values)

    def test_nested_flattened_values(self):
        """
        Flattened values
        """
        resp = Scraper().scrape({
            "find": "^.*$",
            "name": "everything",
            "match": 0,
            "then": {
                'name': 'sentences',
                'find': r'\s?([^.]+)\.',
                'replace': '$1',
                'then': [{
                    'name': 'first word',
                    'find': r'^\w+'
                }, {
                    'name': 'last word',
                    'find': r'\w+$'
                }]
            }
        }, input='roses are red. violets are blue.')
        self.assertEquals({
            'everything': 'roses are red. violets are blue.',
            'sentences': [{
                'sentences': 'roses are red',
                'first word': "roses",
                'last word': 'red'
            }, {
                'sentences': 'violets are blue',
                'first word': 'violets',
                'last word': 'blue'
            }]
        }, resp.flattened_values)

    def test_flattened_overwrite(self):
        """
        Should prefer deeply-nested values
        """
        resp = Scraper().scrape({
            "find": "^.*$",
            "name": "roses",
            "match": 0,
            "then": {
                "name": "roses",
                "find": "^(.*)$",
                "replace": "$1 foobar"
            }
        }, input='red')
        self.assertEquals({
            'roses': 'red foobar'
        }, resp.flattened_values)

    def test_sibling_accessibility(self):
        """
        One-to-one sibling tags should be accessible.
        """
        resp = Scraper().scrape({
            "find": r'\w+ \w+ \w+',
            "name": "three words",
            "then": [{
                "find": r'\w+',
                "match": 0,
                "name": "first"
            }, {
                "find": r'\w+',
                "match": 1,
                "name": "second"
            }, {
                "find": r'\w+',
                "match": 2,
                "name": "third"
            }, {
                "find": ".*",
                "name": "backwards",
                "match": 0,
                "replace": "{{third}} {{second}} {{first}}"
            }]
        }, input='the quick brown fox jumped over the lazy dog')
        self.assertEquals([{
            'three words': 'the quick brown',
            'first': 'the',
            'second': 'quick',
            'third': 'brown',
            'backwards': 'brown quick the'
        }, {
            'three words': 'fox jumped over',
            'first': 'fox',
            'second': 'jumped',
            'third': 'over',
            'backwards': 'over jumped fox'
        }, {
            'three words': 'the lazy dog',
            'first': 'the',
            'second': 'lazy',
            'third': 'dog',
            'backwards': 'dog lazy the'
        }], resp.flattened_values)

    def test_input_instruction(self):
        """
        Possible to specify input in instruction.
        """
        resp = Scraper().scrape({
            "find": r'(roses|violets)',
            "name": "flower",
            "input": "roses are red"
        }, input="violets are blue")
        self.assertEquals({
            "flower": "roses"
        }, resp.flattened_values)

    def test_input_instruction_template(self):
        """
        Possible to parameterize input instruction.
        """
        resp = Scraper().scrape({
            "find": r'(roses|violets)',
            "name": "flower",
            "input": "{{flowers}} are red"
        }, input="violets are blue", tags = {
            "flowers": "roses"
        })
        self.assertEquals({
            "flower": "roses"
        }, resp.flattened_values)

    def test_match_substitution(self):
        """
        Should be possible to use templates in match.
        """
        resp = Scraper().scrape({
            "find": r'\w+',
            "name": "president",
            "match": "{{which}}"
        }, input="washington adams jefferson", tags = {
            "which": "2"
        })
        self.assertEquals({
            "president": "jefferson"
        }, resp.flattened_values)

    def test_match_substitution_min_max(self):
        """
        Should be possible to use templates in min_match and max_match.
        """
        resp = Scraper().scrape({
            "find": r'\w+',
            "name": "president",
            "min_match": "{{begin}}",
            "max_match": "{{end}}"
        }, input="washington adams jefferson", tags = {
            "begin": "1",
            "end": "2"
        })
        self.assertEquals([{
            "president": "adams"
        }, {
            "president": "jefferson"
        }], resp.flattened_values)

    def test_tags_in_instruction(self):
        """
        Should be possible to place tags directly in instruction.
        """
        resp = Scraper().scrape({
            "find": r'{{{flower}}}',
            "name": "flower",
            "tags": {
                "flower": "petunias"
            }
        }, input="violets roses petunias")
        self.assertEquals({
            "flower": "petunias"
        }, resp.flattened_values)

    def test_capture_match_numbers_replace(self):
        """
        Should be possible to capture the number of a match in the replace string.
        """
        resp = Scraper().scrape({
            "find": r'(\w+)',
            "name": "president",
            "tag_match": "which",
            "replace": "$1 was {{which}}"
        }, input="washington adams jefferson")
        self.assertEquals([{
            "president": "washington was 0"
        }, {
            "president": "adams was 1"
        }, {
            "president": "jefferson was 2"
        }], resp.flattened_values)

    def test_capture_match_numbers_in_tags(self):
        """
        Children should have access to the tag_match, too.
        """
        resp = Scraper().scrape({
            "find": r'\w+',
            "tag_match": "which",
            "name": "president",
            "then": {
                "find": r'(\w+)',
                "name": "sentence",
                "input": "first second third",
                "match": "{{which}}",
                "replace": "{{{president}}} was $1"
            }
        }, input="washington adams jefferson")
        self.assertEquals([{
            "president": "washington",
            "sentence": "washington was first"
        }, {
            "president": "adams",
            "sentence": "adams was second"
        }, {
            "president": "jefferson",
            "sentence": "jefferson was third"
        }], resp.flattened_values)

    def test_replace_tag(self):
        """
        Should be able to place arbitrary tags in replace.
        """
        resp = Scraper().scrape({
            "find": r'(\w+)',
            "name": "flower",
            "replace": "$1 are {{{adjective}}}",
            "tags": {
                "adjective": "beautiful"
            }
        }, input="roses")
        self.assertEquals({
            "flower": "roses are beautiful"
        }, resp.flattened_values)

    def test_replace_self(self):
        """
        Should be able to modify a tag in-place.
        """
        resp = Scraper().scrape({
            "find": r'\w+',
            "name": "flower",
            "then": [{
                "find": "^",
                "name": "flower",
                "replace": "{{{flower}}} forever"
            }]
        }, input="roses violets")
        self.assertEquals([{
            "flower": "roses forever"
        }, {
            "flower": "violets forever"
        }], resp.flattened_values)

    def test_ascii_in(self):
        """
        ASCII string in, ascii string out.
        """
        resp = Scraper().scrape({
            "find": r'\w+',
            "name": "flowers"
        }, input="roses violets")
        self.assertIsInstance(resp.flattened_values[0]['flowers'], str)

    def test_utf_8_in(self):
        """
        UTF-8 bytestring in, UTF-8 bytestring out.  Should match words
        characters as expected.
        """
        resp = Scraper().scrape({
            "find": r'\S+',
            "name": "first name",
            "match": 0
        }, input='jos\xc3\xa9 alejandro')
        self.assertEquals({
            "first name": 'jos\xc3\xa9'
        }, resp.flattened_values)

    def test_no_unicode_in(self):
        """
        Matching on unicode is slow.  Please use bytestrings already encoded
        in UTF-8.
        """
        with self.assertRaises(TypeError):
            Scraper().scrape({
                "find": r'\w+',
                "name": "first name",
                "match": 0
            }, input=u'jos\xe9 alejandro')

    def xtest_security_exception(self):
        """
        Test that we get a security exception when going from remote to local
        URI
        """
        # TODO: no "file:" scheme support, don't see any incentive for adding
        # it
        pass

    def test_join(self):
        """
        For multi-match, is possible to join along some value.
        """
        resp = Scraper().scrape({
            "find": r"\w+",
            "name": "joined",
            "join": ", and "
        }, input="peter paul mary")
        self.assertEquals({
            "joined": "peter, and paul, and mary"
        }, resp.flattened_values)


if __name__ == '__main__':
    unittest.main()
