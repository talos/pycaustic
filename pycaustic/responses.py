# -*- coding: utf-8 -*-

import json

class Result(object):
    """
    The successful result of a single instruction.
    """
    def __init__(self, value, children=None):
        self._value = value
        self._as_dict = {
            'value': value
        }
        if children is None:
            self._children = None
        else:
            if isinstance(children, list):
                if len(children) > 0:
                    self._children = children
                    self._as_dict['children'] = [child.as_dict() for child in children]
                else:
                    self._children = None
            elif isinstance(children, Response):
                self._children = [children]
                self._as_dict['children'] = [children.as_dict()]
            else:
                raise TypeError('result children must be response or list')

    def __str__(self):
        return json.dumps(self.as_dict())

    @property
    def value(self):
        return self._value

    @property
    def children(self):
        return self._children

    def as_dict(self, truncated=True):
        if truncated == True and len(self._as_dict['value']) > 200:
            val = self._as_dict['value']
            as_dict = dict(self._as_dict)
            as_dict['value'] = val[:100] + '...' + val[-100:]
            return as_dict
        else:
            return self._as_dict


class Response(object):
    """
    Wrapper for a Caustic response.
    """

    def __init__(self, request):
        self._id = request.id
        self._uri = request.uri
        self._instruction = request.instruction
        self._as_dict = {
            'id': self._id,
            'instruction': self._instruction,
            'uri': self._uri,
            'status': self.status
        }

    def __str__(self):
        return json.dumps(self.as_dict())

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

    def as_dict(self, truncated=True):
        return self._as_dict


class Ready(Response):
    """
    A Response with results. Should be subclassed.
    """
    def __init__(self, request, name, description, results):
        super(Ready, self).__init__(request)
        self._name = name
        self._description = description
        self._results = results
        self._as_dict.update({
            'name': name,
            'description': description,
            'results': [r.as_dict() for r in results]
        })

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
        self._as_dict.update({
            'cookies': cookies.get_dict()
        })

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
        self._as_dict.update({
            'name': name,
            'description': description
        })

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
        self._as_dict.update({
            'missing': missing_tags
        })

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
        self._as_dict.update({
            'failed': reason
        })

    @property
    def reason(self):
        return self._reason

    def _status(self):
        return 'failed'
