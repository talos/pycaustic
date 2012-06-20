# -*- coding: utf-8 -*-

import re
from .errors import TemplateError, TemplateResultError

class Substitution(object):
    """
    A single string substitution operation.
    """

    def __init__(self, template, tags={}, open=r"{{", close=r"}}"):
        self._tags = tags
        self._missing_tags = []
        TEMPLATE_RE = re.compile(open + r'([\w\d]+)' + close)

        # A substitution on None just returns None
        if template is None:
            self._result = None

        # Simple string, sub out components
        elif isinstance(template, basestring):
            self._result = TEMPLATE_RE.sub(self._replace_tag, template)

        # Substitution on dict, sub out each key and value
        elif isinstance(template, dict):
            self._result = {}
            for k, v in template.iteritems():
                subbed_key = TEMPLATE_RE.sub(self._replace_tag, k)
                subbed_val = TEMPLATE_RE.sub(self._replace_tag, v)
                self._result[subbed_key] = subbed_val
        else:
            raise TemplateError("Substitutions can only be made on strings and dicts")

    def _replace_tag(self, match):
        tag_name = match.group(1)
        val = self._tags.get(tag_name)
        if val:
            return val
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

