# -*- coding: utf-8 -*-

import json

class Result(object):
    """
    The successful result of a single instruction.
    """
    def __init__(self, value, children=None):
        self._value = value
        if children is None:
            self._children = None
        else:
            if isinstance(children, list):
                if len(children) > 0:
                    self._children = children
                else:
                    self._children = None
            elif isinstance(children, Response):
                self._children = [children]
            else:
                raise TypeError('result children must be response or list')

    def __str__(self):
        return json.dumps(self.as_dict(), default=lambda x: "Unencodable (%s)" % x)

    @property
    def value(self):
        return self._value

    @property
    def children(self):
        return self._children

    def _construct_dict(self):
        d = {
            'value': self._value
        }
        if self._children:
            d['children'] = [child.as_dict() for child in self._children]
        return d

    def as_dict(self, truncated=True):
        as_dict = self._construct_dict()

        if truncated == True and len(as_dict['value']) > 200:
            val = as_dict['value']
            as_dict['value'] = val[:100] + '...' + val[-100:]
            return as_dict
        else:
            return as_dict


class Response(object):
    """
    Wrapper for a Caustic response.
    """

    def __init__(self, request):
        self._id = request.id
        self._uri = request.uri
        self._tags = request.tags
        self._instruction = request.instruction

    def __str__(self):
        return json.dumps(self.as_dict(), default=lambda x: "Unencodable (%s)" % x)

    @property
    def id(self):
        return self._id

    @property
    def uri(self):
        return self._uri

    @property
    def instruction(self):
        return self._instruction

    @property
    def status(self):
        return self._status()

    def _status(self):
        raise NotImplementedError("Must use subclass")

    def _construct_dict(self):
        return {
            'uri': self._uri,
            'status': self.status,
            'tags': self._tags
        }

    def as_dict(self, truncated=True):
        return self._construct_dict()


class Ready(Response):
    """
    A Response with results. Should be subclassed.
    """
    def __init__(self, request, name, description, results):
        super(Ready, self).__init__(request)
        self._name = name
        self._description = description
        self._results = results

    def _construct_dict(self):
        d = super(Ready, self)._construct_dict()
        d.update({
            'name': self._name,
            'description': self._description,
            'results': [r.as_dict() for r in self._results]
        })
        return d

    @property
    def name(self):
        """
        The name specified in the instruction for this Response.  Is None if
        no name was specified.
        """
        return self._name

    @property
    def description(self):
        return self._description

    @property
    def results(self):
        return self._results

    @property
    def flattened_values(self):
        """
        Obtain a dict or list containing all results, descending as deeply
        as possible. One-to-one relations are flattened.
        """

        flattened_values = []
        for r in self.results:
            branch = {}

            # Only set a value when a name was specified.
            if self.name is not None:
                branch[self.name] = r.value

            if r.children:
                for c in r.children:
                    if isinstance(c, Ready):
                        child_flat_values = c.flattened_values

                        if isinstance(child_flat_values, dict):
                            branch.update(child_flat_values)
                        elif c.name is not None:
                            branch[c.name] = child_flat_values

            flattened_values.append(branch)

        if len(flattened_values) == 1:
            return flattened_values[0]
        else:
            return flattened_values

class DoneFind(Ready):
    """
    The response from a successful find.
    """
    def _status(self):
        return 'found'


class DoneLoad(Ready):
    """
    The response from a successful load.
    """
    def __init__(self, request, name, description, result, cookies):
        super(DoneLoad, self).__init__(request, name, description, [result])
        self._cookies = cookies

    def _construct_dict(self):
        d = super(DoneLoad, self)._construct_dict()
        d.update({
            'cookies': self._cookies.get_dict()
        })
        return d

    @property
    def cookies(self):
        return self._cookies

    def _status(self):
        return 'loaded'


class Wait(Response):
    """
    Wait caustic response.
    """
    def __init__(self, request, name, description):
        super(Wait, self).__init__(request)
        self._name = name
        self._description = description

    def _construct_dict(self):
        d = super(Wait, self)._construct_dict()
        d.update({
            'name': self._name,
            'description': self._description
        })
        return d

    @property
    def name(self):
        return self._name

    def description(self):
        return self._description

    def _status(self):
        return 'wait'


class MissingTags(Response):
    """
    Missing tags caustic response.
    """
    def __init__(self, request, missing_tags):
        super(MissingTags, self).__init__(request)
        self._missing_tags = missing_tags

    def _construct_dict(self):
        d = super(MissingTags, self)._construct_dict()
        d.update({
            'missing': self._missing_tags
        })
        return d

    @property
    def missing_tags(self):
        return self._missing_tags

    def _status(self):
        return 'missing'


class Failed(Response):
    """
    Failure caustic response.
    """
    def __init__(self, request, reason):
        super(Failed, self).__init__(request)
        self._reason = reason

    def _construct_dict(self):
        d = super(Failed, self)._construct_dict()
        d.update({
            'failed': self._reason
        })
        return d

    @property
    def reason(self):
        return self._reason

    def _status(self):
        return 'failed'
