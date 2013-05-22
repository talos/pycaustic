# -*- coding: utf-8 -*-

import requests
import os
import urlparse
import json
import copy
from collections import OrderedDict

from .patterns import Regex
from .responses import ( DoneLoad, DoneFind, Wait, MissingTags,
                         Failed, Result )
from .templates import Substitution, InheritedDict
from .errors import InvalidInstructionError, SchemeSecurityError, PatternError

CURDIR = os.getcwd()
FILE_CACHE = OrderedDict()
MAX_FILE_CACHE_SIZE = 50

class Request(object):

    def __init__(self, instruction, tags, input, force, request_id, uri):
        try:
            input = str(input)
        except UnicodeError:
            raise TypeError("For performance reasons, only bytestrings may be "
                            "read as input.  Please encode as UTF-8 to match on "
                            "extended characters.\n\nOffending string: %s" % input)

        #self._instruction = copy.deepcopy(instruction)
        self._instruction = instruction
        self._tags = tags
        self._input = input
        self._force = force
        self._id = request_id
        self._uri = uri

    @property
    def instruction(self):
        return self._instruction

    @property
    def tags(self):
        return self._tags

    @property
    def input(self):
        return self._input

    @property
    def force(self):
        return self._force

    @property
    def id(self):
        return self._id

    @property
    def uri(self):
        return self._uri


class Loader(object):

    def __init__(self):
        self._gevent = None
        self._grequests = None

    @property
    def gevent(self):
        if self._gevent == None:
            import gevent
            self._gevent = gevent
        return self._gevent

    @property
    def grequests(self):
        if self._grequests == None:
            import grequests
            self._grequests = grequests
        return self._grequests


_loader = Loader()

class Scraper(object):

    def __init__(self, session=None, force_all=False, pool=None):
        self._pool = pool

        if session is None:
            self._session = requests.Session()
        else:
            # We could defensively deepcopy session -- advisable?
            #self._session = copy.deepcopy(session)
            self._session = session
        self._force_all = force_all

    def _load_uri(self, base_uri, uri_to_resolve):
        """
        Obtain a remote instruction.

        Returns the instruction as a python object, along with the resolved uri
        """
        resolved_uri = urlparse.urlsplit(urlparse.urljoin(base_uri, uri_to_resolve))
        base_scheme = urlparse.urlsplit(base_uri).scheme
        if base_scheme is not None and base_scheme != resolved_uri.scheme:
            raise SchemeSecurityError("Cannot cross from '%s' to '%s'" % (
                base_scheme, resolved_uri.scheme))

        try:
            if resolved_uri.scheme in ['http', 'https']:
                instruction = json.loads(requests.get(resolved_uri).text)
            elif resolved_uri.scheme is '':
                resolved_uri_str = urlparse.urlunsplit(resolved_uri)

                # Use our file cache if we can
                instruction = copy.deepcopy(FILE_CACHE.get(resolved_uri_str))

                # Otherwise, load and save in the cache
                if instruction is None:
                    instruction = json.load(open(resolved_uri_str))
                    FILE_CACHE[resolved_uri_str] = copy.deepcopy(instruction)
                    if len(FILE_CACHE) > MAX_FILE_CACHE_SIZE:
                        FILE_CACHE.popitem(last=False)

            else:
                raise InvalidInstructionError("Reference to unsupported scheme '%s'" % (
                    resolved_uri.scheme))
            return instruction, urlparse.urlunsplit(resolved_uri)
        except requests.exceptions.RequestException as e:
            raise InvalidInstructionError("Couldn't load '%s': %s" % (resolved_uri, e))
        except IOError as e:
            raise InvalidInstructionError("Couldn't open '%s': %s" % (resolved_uri, e))
        except ValueError as e:
            raise InvalidInstructionError("Invalid JSON in '%s'" % resolved_uri)

    def _scrape_find(self, req, instruction, description, then):
        """
        Scrape a find instruction
        """
        if 'find' not in instruction:
            raise InvalidInstructionError("Missing regex")

        tags = req.tags
        find_sub = Substitution(instruction['find'], tags)
        replace_unsubbed = instruction.get('replace', '$0')
        name_sub = Substitution(instruction.get('name'), tags)
        tag_match_sub = Substitution(instruction.get('tag_match'), tags)
        join_sub = Substitution(instruction.get('join', None), tags)
        ignore_case = instruction.get('case_insensitive', False)
        multiline = instruction.get('multiline', False)
        dot_matches_all = instruction.get('dot_matches_all', True)

        # Default to full range
        min_match_raw = instruction.get('min_match', 0)
        max_match_raw = instruction.get('max_match', -1)
        match_raw = instruction.get('match', None)

        # Use single match if it was defined
        min_match_sub = Substitution(min_match_raw if match_raw is None else match_raw, tags)
        max_match_sub = Substitution(max_match_raw if match_raw is None else match_raw, tags)

        substitutions = [find_sub, name_sub, min_match_sub, max_match_sub, tag_match_sub,
                         join_sub]
        # Parameterize input if it was supplied
        if 'input' in instruction:
            input_sub = Substitution(instruction['input'], tags)
            substitutions.append(input_sub)
            if not len(input_sub.missing_tags):
                input = input_sub.result
        else:
            input = req.input

        missing_tags = Substitution.add_missing(*substitutions)
        if len(missing_tags):
            return MissingTags(req, missing_tags)

        try:
            min_match = int(min_match_sub.result)
            max_match = int(max_match_sub.result)
        except ValueError as e:
            return Failed(req, "Min_match '%s' or max_match '%s' is not an int: %s" % (
                min_match_sub.result, max_match_sub.result, e))

        join = join_sub.result

        # Python counts a little differently
        single_match = min_match == max_match or join != None
        max_match = None if max_match == -1 else max_match + 1

        # Default to regex as string
        name = name_sub.result if name_sub.result else None

        tag_match = tag_match_sub.result
        tags = req.tags

        try:
            regex = Regex(find_sub.result, ignore_case, multiline, dot_matches_all,
                          replace_unsubbed)

            # This lets through max_match = None, which is OK for generator
            if min_match > -1 and max_match > -1:
                subs = regex.substitutions(input, min_match, max_match)
            # Negative values mean we can't utilize the generator, sadly...
            else:
                subs = [s for s in regex.substitutions(input)][min_match:max_match]

            # Join subs into a single result.
            if join:
                subs = [join.join(subs)]

            greenlets = []
            replaced_subs = []
            # Call children once for each substitution, using it as input
            # and with a modified set of tags.
            for i, s_unsubbed in enumerate(subs):

                fork_tags = InheritedDict(tags)

                # Ensure we can use tag_match in children
                if tag_match:
                    fork_tags[tag_match] = str(i)

                # Fail out if unable to replace.
                s_sub = Substitution(s_unsubbed, fork_tags)
                if s_sub.missing_tags:
                    return MissingTags(req, s_sub.missing_tags)
                else:
                    s_subbed = s_sub.result
                    replaced_subs.append(s_subbed)

                # actually modify our available tags if it was 1-to-1
                if single_match and name is not None:
                    tags[name] = s_subbed

                    # The tag_match name is chosen in instruction, so it's OK
                    # to propagate it -- no pollution risk
                    if tag_match:
                        tags[tag_match] = str(i)

                if name is not None:
                    fork_tags[name] = s_subbed

                if then:
                    child_scraper = Scraper(session=self._session, force_all=self._force_all, pool=self._pool)
                    greenlets.append(child_scraper.scrape_async(then,
                                                                id=req.id,
                                                                tags=fork_tags,
                                                                input=s_subbed,
                                                                uri=req.uri))
                else:
                    greenlets.append(None)
        except PatternError as e:
            return Failed(req, "'%s' failed because of %s" % (instruction['find'], e))

        if len(greenlets) == 0:
            return Failed(req, "No matches for '%s', evaluated to '%s'" % (
                instruction['find'], find_sub.result))

        #gevent.joinall(greenlets)

        # Build Results with responses from greenlets, substitute in tags
        results = []
        for i, replaced_sub in enumerate(replaced_subs):
            g = greenlets[i]
            if g == None:
                child_resps = []
            elif self._pool:
                child_resps = g.get()
            else:
                child_resps = g
            results.append(Result(replaced_sub, child_resps))

        return DoneFind(req, name, description, results)

    def _scrape_load(self, req, instruction, description, then):
        """
        Scrape a load instruction

        :returns: DoneLoad, Wait, MissingTags, or Failed
        """
        if 'load' not in instruction:
            raise InvalidInstructionError("Missing URL in `load` key")

        method = instruction.get('method', 'get')
        if method not in ['head', 'get', 'post']:
            raise InvalidInstructionError("Illegal HTTP method: %s" % method)

        tags = req.tags
        urlSub = Substitution(instruction['load'], tags)
        nameSub = Substitution(instruction.get('name'), tags)
        postsSub = Substitution(instruction.get('posts'), tags)
        cookiesSub = Substitution(instruction.get('cookies', {}), tags)
        headersSub = Substitution(instruction.get('headers', {}), tags)

        # Extract our missing tags, if any
        missing_tags = Substitution.add_missing(urlSub, nameSub, postsSub,
                                                cookiesSub)
        if len(missing_tags):
            return MissingTags(req, missing_tags)

        url = urlSub.result
        name = nameSub.result if nameSub.result else None

        if req.force != True:
            return Wait(req, name, description)

        posts = postsSub.result
        cookies = cookiesSub.result
        headers = headersSub.result

        try:
            opts = dict(url=urlSub.result,
                        cookies=cookies,
                        headers=headers,
                        method=method)
            if method == 'post' or posts:
                opts['data'] = posts
                # Force use of POST if post-data was set.
                opts['method'] = 'post'

            if self._pool is None:
                prepared_req = requests.Request(**opts).prepare()
                resp = self._session.send(prepared_req)
            else:
                grequests = _loader.grequests
                async_req = grequests.AsyncRequest(session=self._session,
                                                   **opts)
                async_req.send()
                resp = async_req.response

            # Make sure we're using UTF-8
            if resp.encoding and resp.encoding.lower() == 'utf-8':
                resp_content = resp.content
            else:
                resp_content = resp.text.encode('utf-8', 'ignore')

            if resp.status_code == 200:
                # Call children using the response text as input
                child_scraper = Scraper(session=self._session, force_all=self._force_all, pool=self._pool)

                scraper_results = child_scraper.scrape(then,
                                                       id=req.id,
                                                       tags=tags,
                                                       input=resp_content,
                                                       uri=req.uri)
                result = Result(resp.text, scraper_results)
                return DoneLoad(req, name, description, result, resp.cookies)
            else:
                return Failed(req, "Status code %s from %s" % (
                    resp.status_code, url))
        except requests.exceptions.RequestException as e:
            return Failed(req, "%s" % e)

    def _extend_instruction(self, orig, extension):
        """
        Extend one instruction with another.  Orig and extension are modified
        in-place!
        """
        # keys that are turned into arrays & extended
        for ex_key in ['extends', 'then']:
            # Nothing to extend, skip out the pop at end
            if ex_key not in extension:
                continue
            # We can just copy it over
            elif ex_key not in orig:
                orig[ex_key] = extension[ex_key]
            else:
                # Wrap the original value in a list
                if not isinstance(orig[ex_key], list):
                    orig[ex_key] = [orig[ex_key]]

                # Insert values at beginning if extension is also list, append otherwise.
                if isinstance(extension[ex_key], list):
                    for i, v in enumerate(extension[ex_key]):
                        orig[ex_key].insert(i, v)
                else:
                    orig[ex_key].insert(0, extension[ex_key])

            # Clear out key for update at end
            extension.pop(ex_key)

        # keys that are updated
        for up_key in ['cookies', 'headers', 'posts']:
            # Nothing to update, skip out pop at end
            if up_key not in extension:
                continue
            # We can just copy it over
            elif up_key not in orig:
                orig[up_key] = extension[up_key]
            # If they're both dicts, then we update.  If not, then a replace
            # will happen.
            else:
                orig_val = orig[up_key]
                up_val = extension[up_key]
                # Prefer orig_val
                if isinstance(orig_val, dict) and isinstance(up_val, dict):
                    up_val.update(orig_val)
                    orig[up_key] = up_val
                # Keep things available for total replacement.
                else:
                    continue

            # Clear out key for update at end
            extension.pop(up_key)

        # everything else is replaced.
        orig.update(extension)

    def _scrape_dict(self, req, instruction):
        """
        Scrape a dict instruction.

        :returns: Response
        """

        while 'extends' in instruction:
            extends = instruction.pop('extends')
            if isinstance(extends, basestring):
                loaded_instruction, target_uri = self._load_uri(req.uri, extends)
                self._extend_instruction(instruction, loaded_instruction)
            elif isinstance(extends, dict):
                self._extend_instruction(instruction, extends)
            elif isinstance(extends, list):
                for ex in extends:
                    if isinstance(ex, basestring):
                        loaded_instruction, target_uri = self._load_uri(req.uri, ex)
                        self._extend_instruction(instruction, loaded_instruction)
                    elif isinstance(ex, dict):
                        self._extend_instruction(instruction, ex)
                    else:
                        raise InvalidInstructionError("element of `extends` list must be a dict or str")
            else:
                raise TypeError()

        # Imperfect solution, but updating tags in request directly
        # should be safe at this point.
        tags = instruction.get('tags', {})
        req.tags.update(tags)

        then = instruction.get('then', [])
        description = instruction.get('description', None)

        if 'find' in instruction:
            return self._scrape_find(req, instruction, description, then)
        elif 'load' in instruction:
            return self._scrape_load(req, instruction, description, then)
        else:
            raise InvalidInstructionError("Could not find `find` or `load` key.")

    def scrape(self, instruction, tags={}, input='', force=False, **kwargs):
        """
        Scrape a request.

        :param: instruction An instruction, either as a string, dict, or list
        :type: str, dict, list
        :param: (optional) tags Tags to use for substitution
        :type: dict
        :param: (optional) input Input for Find
        :type: str
        :param: (optional) force Whether to actually load a load.  Overriden
                by force_all at init-time
        :type: bool
        :param: (optional) uri URI to resolve from
        :type: str
        :param: (optional) id ID for request
        :type: str

        :returns: Response or list of Responses
        """
        uri = kwargs.pop('uri', CURDIR + os.path.sep)
        #req_id = kwargs.pop('id', str(uuid.uuid4()))
        req_id = kwargs.pop('id', None)

        # Override force with force_all
        if self._force_all is True:
            force = True

        # Have to track down the instruction.
        while isinstance(instruction, basestring):
            instructionSub = Substitution(instruction, tags)
            if instructionSub.missing_tags:
                return MissingTags(self, instructionSub.missingTags)
            instruction, uri = self._load_uri(uri, instructionSub.result)

        req = Request(instruction, tags, input, force, req_id, uri)

        # Handle each element of list separately within this context.
        if isinstance(instruction, list):
            if self._pool is None:
                return map(lambda i: Scraper(session=self._session,
                                             force_all=self._force_all,
                                             pool=self._pool
                                            ).scrape(i,
                                                     id=req_id,
                                                     tags=tags,
                                                     input=input,
                                                     force=force,
                                                     uri=uri),
                           instruction)
            else:
                greenlets = map(lambda i: Scraper(session=self._session,
                                                  force_all=self._force_all,
                                                  pool = self._pool
                                                 ).scrape_async(i,
                                                                id=req_id,
                                                                tags=tags,
                                                                input=input,
                                                                force=force,
                                                                uri=uri),
                                instruction)
                _loader.gevent.joinall(greenlets)
                return [g.get() for g in greenlets]

        # Dict instructions are ones we can actually handle
        elif isinstance(instruction, dict):
            return self._scrape_dict(req, instruction)

        # Fail.
        else:
            raise InvalidInstructionError(instruction)

    def scrape_async(self, instruction, tags={}, input='', force=False, **kwargs):
        """
        Scrape a request like `scrape`, except returns a greenlet which
        supplies the Response or list of Responses from `get`.  If concurrency
        was set to 1, then this works the same as scrape.
        """
        if self._pool is None:
            return self.scrape(instruction, tags, input, force=False, **kwargs)
        else:
            return self._pool.spawn(self.scrape, instruction, tags, input, force=False, **kwargs)
