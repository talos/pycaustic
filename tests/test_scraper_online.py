#!/usr/bin/env python
# -*- coding: utf-8 -*-

# These tests do *not* mock out remote calls, and thus need Internet access.

import sys
import os
import json
sys.path.insert(0, os.path.abspath('..'))

from helpers import unittest
from pycaustic import Scraper

FILE_PATH = os.path.abspath(__file__)


class TestSetup(object):

    def setUp(self):
        pass


class TestScraperOnline(TestSetup, unittest.TestCase):

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
            'load': 'http://httpbin.org/post',
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
