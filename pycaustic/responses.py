# -*- coding: utf-8 -*-

class Result(object):
    """
    The successful result of a single instruction.
    """
    def __init__(self, value, children=None):
        self._value = value
        self._children = children
        self._as_dict = {
            'value': value
        }
        if children is not None:
            self._as_dict['children'] = [child._as_dict() for child in children]

    @property
    def value(self):
        return self._value

    @property
    def children(self):
        return self._children

    def as_dict(self):
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

    def as_dict(self):
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
            'results': results
        })

    @property
    def name(self):
        return self._name

    @property
    def description(self):
        return self._description

    @property
    def results(self):
        return self._results


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
            'cookies': cookies
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


class Reference(Response):
    """
    Reference caustic response.
    """
    def __init__(self, request, referenced):
        super(Reference, self).__init__(request)
        self._referenced = referenced
        self._as_dict.update({
            'referenced': referenced
        })

    @property
    def referenced(self):
        return self._referenced

    def _status(self):
        return 'referenced'


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
