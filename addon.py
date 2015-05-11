# -*- coding: utf-8 -*-
"""
    EuroShare.eu Kodi addon
    ~~~~~~~~~~~~~~~~~~

    Watch videos without download via euroshare.eu
    http://euroshare.eu/

    :copyright: (c) 2015 by Jakub Smutný
    :license: GPLv3, see LICENSE.txt for more details.
"""

from xbmcswift2 import Plugin
from resources.lib.api import EuroshareApi, NetworkError

plugin = Plugin()
username = plugin.get_setting('username', unicode)
password = plugin.get_setting('password', unicode)
api = EuroshareApi(username, password, plugin.storage_path)

STRINGS = {
    'not_logged': 30000,
    'credit': 30001,
    'search_video': 30002,
    'network_error': 30010
}


@plugin.route('/')
def show_root_menu():
    """The plugin menu, shows available categories"""
    credit = api.get_credit()
    if credit:
        credit = '[B]' + ': '.join((_T('credit'), credit)) + '[/B]'
    else:
        credit = '[B]' + _T('not_logged') + '[/B]'

    return [
        {'label': credit,
         'path': plugin.url_for('show_root_menu')},
        {'label': _T('search_video'),
         'path': plugin.url_for('search')}
    ]


@plugin.route('/search/')
def search():
    search_string = plugin.keyboard(heading=_T('search_video'))
    if search_string:
        url = plugin.url_for(
            'search_result',
            search_string=search_string
        )
        plugin.redirect(url)


@plugin.route('/search/<search_string>/')
@plugin.route('/search/<search_string>/<page>/', name='search_result_page')
def search_result(search_string, page='0'):
    page = int(page)
    update = page > 0
    if page == 0: # first call
        page = 1

    videos, next_page = api.get_videos(search_string, page)
    items = [{
        'label': video.get('label'),
        'thumbnail': video.get('thumbnail'),
        'info': {
            'size': video.get('size')
        },
        'path': plugin.url_for('get_stream_url', url=video.get('url')),
        'is_playable': True
    } for video in videos]

    if next_page:
        items.insert(0, {
            'label': '[B]Next >>[/B]',
            'path': plugin.url_for(
                'search_result_page',
                search_string=search_string,
                page=str(page + 1)
            )
        })

    if page > 1:
        items.insert(0, {
            'label': '[B]<< Previous[/B]',
            'path': plugin.url_for(
                'search_result_page',
                search_string=search_string,
                page=str(page - 1)
            )
        })

    return plugin.finish(
        items, sort_methods=[('unsorted', '%I'), ('label', '%I'), 'size'],
        update_listing=update
    )


@plugin.route('/stream/<url>/')
def get_stream_url(url):
    """Returns stream URL for specified video file"""
    stream_url = api.get_stream(url)
    return plugin.set_resolved_url(stream_url)


def _T(string_id):
    """Returns the localized string from strings.xml for the given string_id.
    If the string_id is not in known strings, returns string_id.
    """
    if string_id in STRINGS:
        return plugin.get_string(STRINGS[string_id]).encode('utf-8')
    else:
        plugin.log.warning('String is missing: %s' % string_id)
        return string_id


if __name__ == '__main__':
    try:
        plugin.run()
    except NetworkError, error:
        plugin.notify(msg=_T('network_error'))
        plugin.log.error(error)
