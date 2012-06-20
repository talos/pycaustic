# -*- coding: utf-8 -*-

from .errors import PatternError
import re

# Pattern/replacement to turn all unescaped $ followed by
# numbers into backslashes
DOLLAR_PATTERN = re.compile(r'(?<!\\)\$(?=\d+)')
DOLLAR_REPL = r'\\'

# Pattern/replacement to turn all \ followed by numbers into
# format \g<d> (useful because Python recognizes \g<0> but not \0
BS_PATTERN = re.compile(r'\\(\d+)')
BS_REPL = r'\\g<\1>'

# Pattern/replacement to turn escaped $ back into $
UNDOLLAR_PATTERN = re.compile(r'\\\$(?=\d+)')
UNDOLLAR_REPL = r'$'

def _switch_backreferences(input):
    return UNDOLLAR_PATTERN.sub(UNDOLLAR_REPL,
            BS_PATTERN.sub(BS_REPL,
             DOLLAR_PATTERN.sub(DOLLAR_REPL, input)))


class Regex(object):
    """
    Due to differences between the way the prior Java's regex expand templates
    work (particularly named groups and \\ vs $ group names), it's advisable
    to roll our own.

    This also lets us get lists of strings directly via substitutions.
    """


    def __init__(self, regex_str, ignore_case, multiline, dot_matches_all, replace):

        re_flags = 0
        re_flags += re.IGNORECASE if ignore_case else 0
        re_flags += re.MULTILINE if multiline else 0
        re_flags += re.DOTALL if dot_matches_all else 0

        self.regex = re.compile(regex_str, re_flags)
        self.replace = _switch_backreferences(replace)

    def substitutions(self, input):
        """
        Obtain an iterator over replacements from the input via the regex.
        """
        for match in self.regex.finditer(input):
            try:
                yield match.expand(self.replace)
            except re.error as e:
                raise PatternError(e)
