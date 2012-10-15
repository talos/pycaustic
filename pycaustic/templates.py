# -*- coding: utf-8 -*-

import re
import urllib
import numbers
from collections import MutableMapping
from .errors import TemplateError, TemplateResultError

class InheritedDict(MutableMapping):
    """
    A dict that falls back on its parents for all key-misses, but never
    overwrites its parent.
    """

    def __init__(self, parent):
        super(InheritedDict, self).__init__()
        self._parent = parent
        self._this = dict()

    def __setitem__(self, k, v):
        return self._this.__setitem__(k, v)

    def __delitem__(self, k):
        return self._this.__delitem__(k)

    def __getitem__(self, k):
        try:
            return self._this.__getitem__(k)
        except KeyError:
            return self._parent.__getitem__(k)

    def __len__(self, k):
        parent_keys = set(self._parent.keys())
        this_keys = set(self._this.keys())
        return len(parent_keys.union(this_keys))

    def __iter__(self):
        """
        Unclear how to iterate over this and not repeat elements.
        """
        raise NotImplementedError

    def has_key(self, k):
        this_has_key = self._this.has_key(k)
        if this_has_key:
            return this_has_key
        else:
            return self._parent.has_key(k)


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
            try:
                self._result = self._sub(str(template))
            except UnicodeError:
                raise TypeError("Template %s must be a bytestring" % template)
        # Substitution on dict, sub out each key and value
        elif isinstance(template, dict):
            self._result = {}
            for k, v in template.iteritems():
                self._result[self._sub(k)] = self._sub(v)
        # Substitution on number, convert to str
        elif isinstance(template, numbers.Number):
            self._result = self._sub(str(template))
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

