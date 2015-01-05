#!/usr/bin/python
# encoding: utf-8
#
# Copyright © 2014 deanishe@deanishe.net
#
# MIT Licence. See http://opensource.org/licenses/MIT
#
# Created on 2014-12-29
#

"""
Search StackOverflow API
"""

from __future__ import print_function, unicode_literals, absolute_import

import functools
from HTMLParser import HTMLParser
import re
import sys

from workflow import Workflow, web, ICON_WARNING

USER_AGENT = 'Alfred-StackOverflow/{version} ({url})'

UPDATE_SETTINGS = {'github_slug': 'deanishe/alfred-stackoverflow'}

ICON_ANSWERED = 'answered.png'
ICON_UPDATE = 'update-available.png'

# Shown in error logs. Users can find help here
HELP_URL = 'https://github.com/deanishe/alfred-stackoverflow'

# Can be any Stack Exchange site
SITE = 'stackoverflow'

# API endpoint for all Stack Exchange sites
API_URL = 'https://api.stackexchange.com/2.2/search'

# Number of results to fetch from API
RESULT_COUNT = 50

# How long to cache results for
CACHE_MAX_AGE = 20  # seconds

# h.unescape() turns HTML escapes back into real characters
h = HTMLParser()

log = None


def cache_key(query, tags):
    """Make filesystem-friendly cache key"""
    key = query + '_' + ';'.join(tags)
    key = key.lower()
    key = re.sub(r'[^a-z0-9-_;\.]', '-', key)
    key = re.sub(r'-+', '-', key)
    log.debug('Cache key : {!r} {!r} -> {!r}'.format(query, tags, key))
    return key


def handle_answer(api_dict):
    """Extract relevant info from API result"""
    result = {}

    for key in ('title', 'link', 'tags'):
        result[key] = h.unescape(api_dict[key])
    result['answered'] = api_dict['is_answered']

    return result


def get_answers(query=None, tags=None, limit=RESULT_COUNT):
    """Return list of answers from API"""
    headers = {}
    headers['user-agent'] = USER_AGENT.format(version=wf.version,
                                              url=wf.help_url)
    params = {
        'page': 1,
        'pagesize': limit,
        'order': 'desc',
        'sort': 'relevance',
        'site': SITE
    }
    if query:
        params['intitle'] = query
    if tags:
        params['tagged'] = ';'.join(tags)

    r = web.get(API_URL, params, headers=headers)

    log.debug('[{}] {}'.format(r.status_code, r.url))

    r.raise_for_status()

    data = r.json()

    results = [handle_answer(d) for d in data['items']]

    # Sort with answered first
    answered = []
    unanswered = []
    for d in results:
        if d['answered']:
            answered.append(d)
        else:
            unanswered.append(d)

    return answered + unanswered


def main(wf):

    # Update available?
    if wf.update_available:
        wf.add_item('A newer version is available',
                    '↩ to install update',
                    autocomplete='workflow:update',
                    icon=ICON_UPDATE)

    query = wf.args[0].strip()

    # Tag prefix only. Treat as blank query
    if query == '.':
        query = ''

    log.debug('query : {!r}'.format(query))

    if not query:
        wf.add_item('Search StackOverflow')
        wf.send_feedback()
        return 0

    # Parse query into query string and tags
    words = query.split(' ')

    query = []
    tags = []

    for word in words:
        if word.startswith('.'):
            if word != '.':  # Ignore empty tags
                tags.append(word[1:])
        else:
            query.append(word)

    query = ''.join(query)

    key = cache_key(query, tags)

    # Fetch answers from API

    answers = wf.cached_data(key, functools.partial(get_answers, query, tags),
                             max_age=CACHE_MAX_AGE)

    log.debug('{} answers for {!r}, tagged {!r}'.format(len(answers),
                                                        query,
                                                        tags))

    # Show results

    if not answers:
        wf.add_item('No matching answers found',
                    'Try a different query',
                    icon=ICON_WARNING)

    for answer in answers:
        if answer['answered']:
            icon = ICON_ANSWERED
        else:
            icon = 'icon.png'

        wf.add_item(answer['title'],
                    ', '.join(answer['tags']),
                    arg=answer['link'],
                    valid=True,
                    largetext=answer['title'],
                    icon=icon)
        # log.debug(answer)

    wf.send_feedback()


if __name__ == '__main__':
    wf = Workflow(help_url=HELP_URL,
                  update_settings=UPDATE_SETTINGS)
    log = wf.logger
    sys.exit(wf.run(main))
