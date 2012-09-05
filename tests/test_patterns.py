#!/usr/bin/env python
# -*- coding: utf-8 -*-

from helpers import unittest
from pycaustic.patterns import Regex, _switch_backreferences
from pycaustic.errors import PatternError


class TestSwitchBackrefrences(unittest.TestCase):

    def test_no_bs(self):
        """
        Appropriate name.  Should do nothing.
        """
        self.assertEquals('foobar', _switch_backreferences('foobar'))

    def test_escapes(self):
        """
        We should be able to escape $ when followed by numbers
        """
        self.assertEquals('$100', _switch_backreferences(r'\$100'))

    def test_not_escapes(self):
        """
        We should not escape $ when it's followed by something else
        """
        self.assertEquals(r'\$foo', _switch_backreferences(r'\$foo'))

    def test_backslash_alone(self):
        """
        Should insert a properly numbered backslash in place of single $
        backreference
        """
        self.assertEquals(r'\g<0>', _switch_backreferences(r'$0'))

    def test_backslash_in_string(self):
        """
        Should insert a properly numbered backslash in place of $ reference
        in midst of string
        """
        self.assertEquals(r'foo\g<0>bar',
                          _switch_backreferences(r'foo$0bar'))

    def test_backslashes_alone(self):
        """
        Should insert a properly numbered backslashes in place of $
        backreferences
        """
        self.assertEquals(r'\g<0>\g<2>\g<100>',
                          _switch_backreferences(r'$0$2$100'))

    def test_backslashes_in_string(self):
        """
        Should insert a properly numbered backslashes in place of $
        backreferences
        """
        self.assertEquals(r'foo\g<0>bar\g<2>baz\g<100>boo',
                          _switch_backreferences(r'foo$0bar$2baz$100boo'))


class TestRegex(unittest.TestCase):

    def test_no_matches(self):
        """
        Test zero-length list from no matches
        """
        r = Regex('foo', False, False, False, '$0')
        subs = [sub for sub in r.substitutions('bar')]
        self.assertEquals([], subs)

    def test_single_substitution(self):
        """
        Test a single simple match for entire group.
        """
        r = Regex('foo', False, False, False, '$0')
        subs = [sub for sub in r.substitutions('foobar')]
        self.assertEquals(['foo'], subs)

    def test_multiple_substitution(self):
        """
        Test a simple match causing several substitutions.
        """
        r = Regex('foo', False, False, False, '$0')
        subs = [sub for sub in r.substitutions('foo foo foobar foo')]
        self.assertEquals(['foo', 'foo', 'foo', 'foo'], subs)

    def test_bad_group(self):
        """
        Test that a bad group throws an exception we know about.
        """
        r = Regex('foo', False, False, False, '$1')
        with self.assertRaises(PatternError):
            r.substitutions('foo').next()

    def test_several_substitutions(self):
        """
        Test a few substitutions
        """
        r = Regex(r'\w(\w+)', False, False, False, '$0FOO$1')
        subs = [sub for sub in r.substitutions('the quick brown')]
        self.assertEquals(['theFOOhe', 'quickFOOuick', 'brownFOOrown'], subs)

    def test_unbalanced(self):
        """
        We should catch unbalanced parentheses.
        """
        with self.assertRaises(PatternError):
            r = Regex(r'(', False, False, False, '$0')


if __name__ == '__main__':
    unittest.main()
