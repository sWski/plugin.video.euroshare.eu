# -*- coding: utf-8 -*-
"""
    resources.lib.api
    ~~~~~~~~~~~~~~~~~~

    Implementation of euroshare.eu API.

    :copyright: (c) 2015 by Jakub Smutný
    :license: GPLv3, see LICENSE.txt for more details.
"""
from urllib import urlencode
from urllib2 import urlopen, Request, HTTPError, URLError, build_opener, \
                    install_opener, HTTPCookieProcessor
from cookielib import LWPCookieJar
from BeautifulSoup import BeautifulSoup
from math import ceil

BASE_URL = 'http://euroshare.eu'
LOGIN_URL = '/?do=prihlaseni-submit'
COOKIE_FILE = 'cookies.txt'


class NetworkError(Exception):
    pass


class EuroshareApi():

    USER_AGENT = (
        'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:37.0) '
        'Gecko/20100101 Firefox/37.0'
    )

    def __init__(self, username, password, storage_path):
        self.logged_in = False
        self.username = username
        self.password = password
        self.cj = LWPCookieJar(storage_path + COOKIE_FILE)
        try:
            self.cj.load()
        except IOError:
            pass
        else:
            self.logged_in = True
        self.opener = build_opener(HTTPCookieProcessor(self.cj))
        self.opener.addheaders = [('User-Agent', self.USER_AGENT)]

    def get_credit(self):
        data = self.__api_call('/user/informacie')
        return self._parse_credit(data)

    def get_videos(self, query, page=None):
        params = {
            'filter': 'video',
            'sort': 'hodnoceni',
            'q': query,
            'streamOnly': 1
        }
        if page > 1:
            params['strankovani-page'] = page
        data = self.__api_call('/files/search', params)
        return self._parse_results(data)

    def get_stream(self, url):
        data = self.__urlopen(url)
        container = BeautifulSoup(data).find('div', id='obsah').div
        video = container.find('video')
        if video:
            url = video.source['src']
        else:
            url = container.find('p', 'text-vpravo').a['href']
        #print 'url: ' + url
        return url

    @staticmethod
    def _parse_credit(info):
        data = BeautifulSoup(info).find('li', 'price-list').a.string.split(':')
        if len(data) > 1:
            return data[1].strip()
        return None

    @staticmethod
    def _parse_results(data):

        def convert_size(size_str):
            """Converts size to bytes from xxx (kB | MB | GB)"""
            try:
                size, units = size_str.strip().lower().split()
            except ValueError:
                print '_convert_size(): wrong size - ' + repr(size_str)
                return 0

            if 'kb' in units:
                mult = 1024
            elif 'mb' in units:
                mult = 1024 * 1024
            elif 'gb' in units:
                mult = 1024 * 1024 * 1024
            else:
                mult = 1
            return int(ceil(float(size) * mult))

        elems = BeautifulSoup(data).find('div', id='snippet--hledani')
        if not elems:
            return [], None

        elems = elems.findAll('p', 'image-result')
        items = []
        for elem in elems:
            img = elem.find('img')['src']
            if img.startswith('/'):
                img = BASE_URL + img
            items.append({
                'label': elem.find('span', title=True).text.encode('utf-8'),
                'size': convert_size(elem.find('strong').text),
                'thumbnail': img,
                'url': BASE_URL + elem.find('a')['href']
            })

        pages = BeautifulSoup(data).find('p', 'stranky')
        next_page = None
        if pages:
            actual = pages.find('span', 'aktualni')
            next_elem = actual.findNextSibling('a', 'tlacitko')
            if next_elem:
                next_page = int(next_elem.string)
        return items, next_page

    def __login(self):
        if self.username and self.password:
            data = {
                'username': self.username,
                'password': self.password,
                'remember': 'on',
                'send': 'PRIHLÁSENIE'
            }
            if self.__urlopen(BASE_URL + LOGIN_URL, data):
                self.logged_in = True
                self.cj.save()

    def __api_call(self, path, params=None):
        url = BASE_URL + path
        if params:
            url += '?%s' % urlencode(params)
        if not self.logged_in:
            self.__login()
        return self.__urlopen(url)

    def __urlopen(self, url, data=None):
        print 'Opening url: %s' % url
        if data:
            data = urlencode(data)
        try:
            response = self.opener.open(url, data).read()
        except HTTPError, error:
            raise NetworkError('HTTPError: %s' % error)
        except URLError, error:
            raise NetworkError('URLError: %s' % error)
        return response
