#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import json
sys.path.insert(0, os.path.abspath('..'))

from helpers import unittest
from pycaustic import Scraper

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

    def test_needs_force(self):
        """
        Don't load anything without force!
        """
        resp = Scraper().scrape({'load':'http://www.google.com'})
        self.assertEquals('wait', resp.status)

    def test_force_post(self):
        """
        We make a post request if any post-values were defined.
        """
        resp = Scraper().scrape({
            'load': 'http://www.httpbin.org/post',
            'posts': {
                'roses': 'red',
                'violets': 'blue'
            }
        }, force=True)
        self.assertEquals('loaded', resp.status)
        bin_content = json.loads(resp.results[0].value)
        self.assertEquals({
            'roses': 'red',
            'violets': 'blue'
        }, bin_content['form'])

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

    def test_simple_google_request(self):
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

if __name__ == '__main__':
    unittest.main()
