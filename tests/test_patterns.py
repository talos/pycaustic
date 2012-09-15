#!/usr/bin/env python
# -*- coding: utf-8 -*-

from helpers import unittest
from pycaustic.patterns import Regex, _switch_backreferences
from pycaustic.errors import PatternError


class TestSwitchBackrefrences(unittest.TestCase):

    # These tests are all disabled when using re2, since substitutions no
    # longer can be done on $0 (which was the major sticking point)

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
        self.assertEquals(r'\0', _switch_backreferences(r'$0'))

    def test_backslash_in_string(self):
        """
        Should insert a properly numbered backslash in place of $ reference
        in midst of string
        """
        self.assertEquals(r'foo\0bar',
                          _switch_backreferences(r'foo$0bar'))

    def xtest_backslashes_alone(self):
        """
        Should insert a properly numbered backslashes in place of $
        backreferences
        """
        self.assertEquals(r'\0\2\100',
                          _switch_backreferences(r'$0$2$100'))

    def xtest_backslashes_in_string(self):
        """
        Should insert a properly numbered backslashes in place of $
        backreferences
        """
        self.assertEquals(r'foo\0bar\2baz\g100boo',
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

    # Disabled because $0 is not supported as an expansion with re2.
    def xtest_several_substitutions_0_1(self):
        """
        Test a few substitutions, with $0
        """
        r = Regex(r'\w(\w+)', False, False, False, '$0FOO$1')
        subs = [sub for sub in r.substitutions('the quick brown')]
        self.assertEquals(['theFOOhe', 'quickFOOuick', 'brownFOOrown'], subs)

    # Alternative to test above
    def test_several_substitutions_1_2(self):
        """
        Test a few substitutions, without $0
        """
        r = Regex(r'(\w)(\w+)', False, False, False, '$1FOO$2')
        subs = [sub for sub in r.substitutions('the quick brown')]
        self.assertEquals(['tFOOhe', 'qFOOuick', 'bFOOrown'], subs)

    def test_unbalanced(self):
        """
        We should catch unbalanced parentheses.
        """
        with self.assertRaises(PatternError):
            Regex(r'(', False, False, False, '$0')

    def test_range(self):
        """
        Should get the whole range by default.
        """
        r = Regex(r'\w+', False, False, False, '$0')
        subs = [sub for sub in r.substitutions('the quick brown fox')]
        self.assertEquals(['the', 'quick', 'brown', 'fox'], subs)

    def test_beginning(self):
        """
        Support for explicit beginning range.
        """
        r = Regex(r'\w+', False, False, False, '$0')
        subs = [sub for sub in r.substitutions('the quick brown fox', 0, 2)]
        self.assertEquals(['the', 'quick'], subs)

    def test_middle_slice(self):
        """
        Support for explicit middle slice.
        """
        r = Regex(r'\w+', False, False, False, '$0')
        subs = [sub for sub in r.substitutions('the quick brown fox', 1, 3)]
        self.assertEquals(['quick', 'brown'], subs)

    def test_middle_single(self):
        """
        Support for explicit single word in middle.
        """
        r = Regex(r'\w+', False, False, False, '$0')
        subs = [sub for sub in r.substitutions('the quick brown fox', 2, 3)]
        self.assertEquals(['brown'], subs)

if __name__ == '__main__':
    unittest.main()
