# -*- coding: utf-8 -*-

from .errors import PatternError
try:
    import re2 as re
    assert re # quiet pyflakes!
except ImportError:
    import re

# Pattern/replacement to turn all unescaped $ followed by
# numbers into backslashes
DOLLAR_PATTERN = re.compile(r'(?<!\\)\$(?=\d+)')
DOLLAR_REPL = r'\\'

# Pattern/replacement to turn all \ followed by numbers into
# format \g<d> (useful because Python recognizes \g<0> but not \0
BS_PATTERN = re.compile(r'\\(\d+)')
BS_REPL = r'\\\1'

# Pattern/replacement to turn escaped $ back into $
UNDOLLAR_PATTERN = re.compile(r'\\\$(?=\d+)')
UNDOLLAR_REPL = r'$'

def _switch_backreferences(input):
    return UNDOLLAR_PATTERN.sub(UNDOLLAR_REPL,
            BS_PATTERN.sub(BS_REPL,
             DOLLAR_PATTERN.sub(DOLLAR_REPL, input)))

#def _switch_backreferences(input):
#    return DOLLAR_PATTERN.sub(DOLLAR_REPL, input)

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
        re_flags += re.UNICODE

        try:
            self.regex = re.compile(regex_str, re_flags)
        except re.error as e:
            raise PatternError(e)

        # re2 raises different errors
        #except Exception as e:
        #    raise PatternError(e)

        # Don't bother with template expansion on these
        self._notemplate = replace == '$0'

        # TEMP: re2 doesn't support template expansion on $0.  Why would you
        # want to, anyway?
        if not self._notemplate and replace.find('$0') > -1:
            raise PatternError("$0 is not supported in template expansion")

        try:
            self.replace = str(_switch_backreferences(replace))
        except UnicodeError:
            raise TypeError("For performance reasons, the replacement may only " +
                           " be performed with a byte strings.  Please decode to " +
                            " UTF-8 and try again. Offending string: %s" % replace)

    def substitutions(self, input, min_match=0, max_match=None):
        """
        Obtain an iterator over replacements from the input via the regex.
        """

        # re2 is much faster with byte strings.  Only pass it byte strings
        # in UTF-8.
        try:
            input = str(input)
        except UnicodeError:
            raise TypeError("For performance reasons, substitutions may only " +
                           " be performed on byte strings.  Please decode to " +
                            " UTF-8 and try again. Offending string: %s" % input)

        for i, match in enumerate(self.regex.finditer(input)):

            if i < min_match:
                continue
            elif max_match != None and i >= max_match:
                break

            try:
                if self._notemplate:
                    yield match.string[match.start():match.end()]
                else:
                    yield match.expand(self.replace)
            except re.error as e:
                raise PatternError(e)

            # re2 raises different errors
            except IndexError as e:
                raise PatternError(e)
