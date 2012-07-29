# -*- coding: utf-8 -*-

class CausticError(StandardError):
    """
    Base class for all errors from Caustic
    """
    pass


class InvalidInstructionError(CausticError):
    """
    An error resulting from an invalid instruction.
    """
    pass


class PatternError(CausticError):
    """
    Class to absorb errors from re.  This provides some flexibility in case
    we want bad to prevent dynamic substitutions (ie {{foo}} -> $1 when
    there's no first parenthetical group) from blowing things up.
    """
    pass


class TemplateError(CausticError):
    """
    An error from a bad template.
    """
    pass


class TemplateResultError(TemplateError):
    """
    An error from illegal access to a the result property of a template.
    """
    pass


class SchemeSecurityError(CausticError):
    """
    An error that is thrown when an unsafe scheme conversion is attempted
    (any scheme to local).
    """
