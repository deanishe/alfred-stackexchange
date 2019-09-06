#!/usr/bin/python
# encoding: utf-8
#
# Copyright (c) 2014 deanishe@deanishe.net
#
# MIT Licence. See http://opensource.org/licenses/MIT
#
# Created on 2014-12-29
#

"""Search StackOverflow API."""

from __future__ import print_function, absolute_import

from collections import namedtuple
import functools
import hashlib
from HTMLParser import HTMLParser
from unicodedata import normalize
import os
import re
import sys

from workflow import Workflow3, web, ICON_WARNING
from workflow.background import run_in_background, is_running

from common import CLIENT_ID, CLIENT_KEY
from util import asciify

USER_AGENT = 'Alfred-StackOverflow/{version} ({url})'

UPDATE_SETTINGS = {'github_slug': 'deanishe/alfred-stackoverflow'}

ICON_ANSWERED = 'answered.png'
ICON_UPDATE = 'update-available.png'

# Shown in error logs. Users can find help here
HELP_URL = 'https://github.com/deanishe/alfred-stackoverflow'

# Can be any StackExchange site
DEFAULT_SITE = os.getenv('site_id') or 'stackoverflow'

# API endpoint for all StackExchange sites
API_URL = 'https://api.stackexchange.com/2.2/search/advanced'
# Returns list of all StackExchange sites
SITES_URL = 'https://api.stackexchange.com/2.2/sites'

# Cache key for sites list
SITES_KEY = 'all-sites'

# Number of results to fetch from API
RESULT_COUNT = int(os.getenv('result_count') or 50)

# How long to cache results for
CACHE_MAX_AGE = int(os.getenv('cache_max_age') or 20)  # seconds

# Don't list meta sites in results
IGNORE_META = os.getenv('ignore_meta_sites') in ('1', 'true', 'yes')

# Check mark to overlay on icons
CHECK_MARK = 'check.png'

USAGE = """so.py [options] <query>

Search StackExchange sites.

Usage:
    so.py search [--site <id>] <query>
    so.py sites [<query>]
    so.py set-default
    so.py reveal-icon
    so.py cache-sites
    so.py (-h | --help)
    so.py --version

Options:
    -s, --site <id>    API name of site to search [default: {default}]
    -h, --help         show this message and exit
    --version          show version number and exit
""".format(default=DEFAULT_SITE)


# Used to unescape HTML entities
h = HTMLParser()
# Logger populated in if __name__ == '__main__' clause
log = None


# API responses
Site = namedtuple('Site', 'id name audience icon is_meta')
Answer = namedtuple('Answer', 'title link tags answered')


def site_from_env():
    """Return a ``Site`` based on environment/workflow variables."""
    return Site(
        os.getenv('site_id'),
        os.getenv('site_name'),
        os.getenv('site_audience'),
        os.getenv('site_icon'),
        os.getenv('site_is_meta') == '1',
    )


def unicodify(s, encoding='utf-8'):
    """Ensure ``s`` is Unicode.

    Returns Unicode unchanged, decodes bytestrings and calls `unicode()`
    on anything else.

    Args:
        s (basestring): String to convert to Unicode.
        encoding (str, optional): Encoding to use to decode bytestrings.

    Returns:
        unicode: Decoded Unicode string.

    """
    if isinstance(s, unicode):
        return s

    if isinstance(s, str):
        return s.decode(encoding, 'replace')

    return unicode(s)


def asciify(s):
    """Ensure string only contains ASCII characters.

    Args:
        s (basestring): Unicode or bytestring.

    Returns:
        unicode: String containing only ASCII characters.

    """
    u = normalize('NFD', unicodify(s))
    s = u.encode('us-ascii', 'ignore')
    return unicodify(s)


def _hash(s):
    """Return hash of string."""
    if isinstance(s, unicode):
        s = s.encode('utf-8')
    h = hashlib.md5(s)
    return h.hexdigest()[:12]


def cache_key(site_id, query, tags):
    """Make filesystem-friendly cache key."""
    key = query
    if tags:
        key += '_' + '+'.join(tags)
    h = _hash(key)
    key = asciify(key)
    key = key.lower()
    key = re.sub(r'[^a-z0-9-_;\.]', '-', key) + '-' + h
    key = 'search/' + site_id + '/' + re.sub(r'-+', '-', key)
    dirpath = os.path.dirname(wf.cachefile(key))
    if not os.path.exists(dirpath):
        os.makedirs(dirpath)
    log.debug('cache key : %r %r %r -> %r', site_id, query, tags, key)
    return key


def get_url(url, **params):
    """Retrieve URL using API headers and parameters.

    Args:
        url (str): URL to fetch.
        **params: Query-string parameters.
    """
    # Application ID. Allows up to 10K API hits/day per IP.
    params.update({'key': 'FgLEU6zgwYULvStDmrgqxg((', 'client_id': '16105'})
    headers = {
        'User-Agent': USER_AGENT.format(version=wf.version, url=wf.help_url)
    }
    r = web.get(url, params, headers=headers)
    log.debug(u'[%d] %s', r.status_code, r.url)
    r.raise_for_status()
    return r


def api_call(url, **params):
    """Return response from API."""
    data = get_url(url, **params).json()
    remaining = data.get('quota_remaining') or 0
    total = data.get('quota_max') or 0
    if total and remaining:
        log.info(u'%d/%d API requests remaining', remaining, total)
    return data


def get_sites():
    """Retrieve list of available StackExchange sites."""
    sites = []
    page = 1
    while True:
        log.debug(u'[sites] fetching page %d ...', page)
        data = api_call(SITES_URL, pagesize=100, page=page)

        for d in data.get('items', []):
            if d['site_state'] == 'closed_beta':
                log.debug('[sites] ignored %r (closed beta)',
                          d['api_site_parameter'])
                continue

            sites.append(Site(
                h.unescape(d['api_site_parameter']),
                h.unescape(d['name']),
                h.unescape(d['audience']),
                d['icon_url'],
                d['site_type'] == 'meta_site',
            ))

        if not data.get('has_more'):
            break

        page += 1

    return sites


def handle_answer(api_dict):
    """Extract relevant info from API result."""
    return Answer(
        h.unescape(api_dict['title']),
        h.unescape(api_dict['link']),
        tuple(h.unescape(api_dict['tags'])),
        api_dict['is_answered'],
    )


def get_answers(site_id, query=None, tags=None, limit=RESULT_COUNT):
    """Return list of answers from API."""
    params = {
        'page': 1,
        'pagesize': limit,
        'order': 'desc',
        'sort': 'relevance',
        'site': site_id
    }
    if query:
        params['q'] = query
    if tags:
        params['tagged'] = ';'.join(tags)

    data = api_call(API_URL, **params)
    answers = [handle_answer(d) for d in data['items']]

    # Sort with answered first
    answers.sort(key=lambda a: not a.answered)
    return answers


def icon_path(site_id, answered=False):
    """Return local path for site icon.

    Args:
        site_id (str): Site whose icon path should be returned.
        answered (bool, optional): Return version of icon with check mark.

    Returns:
        str: Path to icon.
    """
    suffix = '-answered' if answered else ''
    return wf.cachefile('icons/%s%s.png' % (site_id, suffix))


def site_icon(site_id, answered=False, default=None):
    """Return locally-cached icon for ``site`` or ``default``.

    Args:
        site_id (str): Site whose icon should be returned.
        answered (bool, optional): Return version of icon with check mark.
        default (None, optional): Default to return if icon is not cached.

    Returns:
        str: Path to icon file.
    """
    p = icon_path(site_id, answered)
    if os.path.exists(p):
        return p

    return default


def do_cache_sites(args):
    """Update cached list of sites and download icons."""
    sites = get_sites()
    log.debug(u'[sites] retrieved %d StackExchange sites', len(sites))
    wf.cache_data(SITES_KEY, sites)
    icons = [s for s in sites if site_icon(s) is None]
    if icons:
        from icons import overlay
        dirpath = wf.cachefile('icons')
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)
        log.debug('[sites] caching %d icons', len(icons))
        for s in icons:
            p = icon_path(s.id)
            try:
                r = get_url(s.icon)
                r.save_to_path(p)
                overlay(p, CHECK_MARK, icon_path(s.id, True))
            except Exception as err:
                log.error('[icons] failed to cache icon for %r: %s', s.id, err)


def do_reveal_icon(args):
    """Reveal site icon in Finder."""
    from workflow.notify import notify
    from workflow.util import applescriptify, run_applescript
    s = site_from_env()
    log.debug('[reveal] site=%r', s)
    p = icon_path(s.id)
    if not os.path.exists(p):
        notify(u'Error',
               u'Icon for “{s.name}” has not been downloaded'.format(s=s))
    script = u"""
    tell application "Finder"
        reveal POSIX file "{}"
        activate
    end tell
    """.format(applescriptify(p))
    run_applescript(script)


def do_set_default(args):
    """Set site as default."""
    from workflow.util import run_trigger, set_config
    from workflow.notify import notify
    s = site_from_env()
    log.debug('[default] site=%r', s)
    set_config('site_id', s.id, exportable=True)
    set_config('site_name', s.name, exportable=True)
    run_trigger('search')
    notify(u'Updated Settings',
           u'Default site changed to “{s.name}”'.format(s=s))


def do_sites(args):
    """Script Filter to choose a StackExchange site."""
    updating = False
    sites = wf.cached_data(SITES_KEY, None, 0)
    if not sites:
        updating = True
        wf.add_item(u'Updating List of Sites…',
                    u'Please wait a few moments',
                    valid=False)
        wf.rerun = 0.2
        wf.send_feedback()
        return

    # Set rerun in case sites/icons are being updated
    if updating or is_running('sites'):
        wf.rerun = 0.3

    if IGNORE_META:
        sites = [s for s in sites if not s.is_meta]

    query = args['<query>'].strip()
    if query:
        sites = wf.filter(query, sites, key=lambda s: s.name)

    for s in sites:
        it = wf.add_item(s.name,
                         s.audience,
                         icon=site_icon(s.id, default='icon.png'),
                         uid=s.id,
                         copytext=s.id,
                         valid=True)

        it.setvar('site_id', s.id)
        it.setvar('site_name', s.name)
        it.setvar('site_audience', s.audience)
        it.setvar('site_icon', s.icon)
        it.setvar('site_is_meta', '1' if s.is_meta else '0')

        # Alternate actions
        mod = it.add_modifier('cmd', u'Set as default site')
        mod.setvar('action', 'set-default')
        mod = it.add_modifier('alt', u'Reveal icon in Finder')
        mod.setvar('action', 'reveal-icon')

    wf.warn_empty(u'No Matching Sites', u'Try a different query')
    wf.send_feedback()


def do_search(args):
    """Script Filter to search StackExchange site."""
    # Update available?
    if wf.update_available:
        wf.add_item(u'A newer version is available',
                    u'↩ to install update',
                    autocomplete='workflow:update',
                    icon=ICON_UPDATE)

    query = args['<query>'].strip()
    site_id = args['--site']

    # Set rerun in case sites/icons are being updated
    if is_running('sites'):
        wf.rerun = 0.3

    # Tag prefix only. Treat as blank query
    if query == '.':
        query = ''

    log.debug(u'site=%r, query=%r', site_id, query)

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

    query = ' '.join(query)

    # Fetch answers from API
    answers = wf.cached_data(
        cache_key(site_id, query, tags),
        functools.partial(get_answers, site_id, query, tags),
        max_age=CACHE_MAX_AGE,
    )
    log.info(u'%d answers for query %r and tags %r',
             len(answers), query, ', '.join(tags))

    # Show results
    for a in answers:
        wf.add_item(a.title,
                    ', '.join(a.tags),
                    arg=a.link,
                    uid=a.link,
                    valid=True,
                    largetext=a.title,
                    icon=site_icon(site_id, a.answered, 'icon.png'))

    wf.warn_empty(u'No Answers Found', u'Try a different query')
    wf.send_feedback()


def main(wf):
    """Run workflow."""
    from docopt import docopt
    args = docopt(USAGE, wf.args, version=wf.version)
    log.debug('args=%r', args)

    if not wf.cached_data_fresh(SITES_KEY, 86400) and not is_running('sites'):
        log.debug(u'Updating list of sites…')
        run_in_background('sites', ('/usr/bin/python', 'so.py', 'cache-sites'))

    if args['search']:
        return do_search(args)

    if args['sites']:
        return do_sites(args)

    if args['cache-sites']:
        return do_cache_sites(args)

    if args['reveal-icon']:
        return do_reveal_icon(args)

    if args['set-default']:
        return do_set_default(args)


if __name__ == '__main__':
    wf = Workflow3(help_url=HELP_URL,
                   update_settings=UPDATE_SETTINGS)
    log = wf.logger
    sys.exit(wf.run(main))
