# -*- coding: utf-8 -*-

import re
import urllib
from .errors import TemplateError, TemplateResultError

class Substitution(object):
    """
    A single string substitution operation.
    """

    def __init__(self, template, tags={},
                 open_encoded='{{', close_encoded='}}',
                 open_unencoded='{{{', close_unencoded='}}}'):
        self._tags = tags
        self._missing_tags = []
        self._encoded_re = re.compile(open_encoded + r'([\w\d]+)' + close_encoded)
        self._unencoded_re = re.compile(open_unencoded + r'([\w\d]+)' + close_unencoded)

        # A substitution on None just returns None
        if template is None:
            self._result = None
        # Simple string, sub out components
        elif isinstance(template, basestring):
            self._result = self._sub(template)

        # Substitution on dict, sub out each key and value
        elif isinstance(template, dict):
            self._result = {}
            for k, v in template.iteritems():
                self._result[self._sub(k)] = self._sub(v)
        else:
            raise TemplateError("Substitutions can only be made on strings and dicts")

    def _sub(self, template):
        tmp = self._unencoded_re.sub(self._replace_tag_unencoded, template)
        return self._encoded_re.sub(self._replace_tag_encoded, tmp)

    def _replace_tag_unencoded(self, match):
        return self._replace_tag(match, False)

    def _replace_tag_encoded(self, match):
        return self._replace_tag(match, True)

    def _replace_tag(self, match, encode):
        tag_name = match.group(1)
        if self._tags.has_key(tag_name):
            val = self._tags.get(tag_name)
            return val if not encode else urllib.quote_plus(val, safe='')
        else:
            self._missing_tags.append(tag_name)

    @property
    def missing_tags(self):
        return self._missing_tags

    @property
    def result(self):
        if len(self.missing_tags):
            raise TemplateResultError()
        return self._result

    @classmethod
    def add_missing(cls, *substitutions):
        """
        Add together all the missing tags from a series of substitutions
        """
        missing_tags = []
        for sub in substitutions:
            if sub.missing_tags:
                missing_tags.append(sub.missing_tags)
        return missing_tags

