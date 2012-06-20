#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
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


    def xtest_simple_google_request(self):
        """
        Test a very straightforward request to Google to look for "I'm feeling
        lucky".
        """
        instruction = {
            "load"  : "http://www.google.com",
            "then" : {
                "find" : "Feeling\\s[\\w]*",
                "name" : "Feeling?"
            }
        }
        resp = Scraper(instruction).scrape()

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
        self.assertEquals('lucky', result.value)

        # And which has no children
        self.assertIsNone(result.children)

if __name__ == '__main__':
    unittest.main()
