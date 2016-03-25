# -*- coding: utf-8 -*-
"""
    Copyright: (c) 2015 linuxwhatelse (info@linuxwhatelse.de)
    License: GPLv3, see LICENSE for more details

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


__author__    = 'linuxwhatelse'
__email__     = 'info@linuxwhatelse.com'
__copyright__ = 'Copyright 2016, linuxwhatelse'
__license__   = 'GPLv3'

__version__   = '0.1.0'

import sys
import os
import traceback

from http import server, cookies
import json
import datetime

import mapper

validator = None
validator_excludes = None

class _RequestHandler(server.BaseHTTPRequestHandler):
    _mpr         = mapper.Mapper()

    _status_code = None
    _message     = None
    _cookie      = None
    _payload     = None

    def do_GET(self):
        if not self._validate():
            return

        try:
            resp = self._mpr.call(url=self.path, method='GET',
                args={'headers': self.headers})

        except Exception as e:
            traceback.print_exc()
            self._send_error(e)
            return

        if resp:
            self._handle_mapper_response(resp)

            self.send_response(self._status_code, self._message)
            self.send_header('Content-type', 'application/json')
            self._send_default_headers()
            self.end_headers()

            if self._payload != None:
                self.wfile.write(bytes(json.dumps(self._payload,
                    default=self._serialize), 'utf-8'))

            else:
                self.wfile.write(bytes(json.dumps([]), 'utf-8'))

        else:
            self.send_response(400)
            self._send_default_headers()
            self.end_headers()

    def do_POST(self):
        if not self._validate():
            return

        content_length = int(self.headers['Content-Length'])

        try:
            data = self.rfile.read(content_length).decode('utf-8')
            if data:
                data = json.loads(data)
            else:
                data = {}

        except Exception as e:
            traceback.print_exc()
            self._send_error('Received invalid json')
            return

        try:
            resp = self._mpr.call(url=self.path, method='POST',
                args={'headers': self.headers, 'payload': data})

        except Exception as e:
            traceback.print_exc()
            self._send_error(e)
            return

        if resp:
            self._handle_mapper_response(resp)

            self.send_response(self._status_code, self._message)
            self.send_header('Content-type', 'application/json')
            self._send_default_headers()

            if self._cookie:
                self.send_header('Set-Cookie', self._cookie.output(header=''))

            self.end_headers()

        else:
            self.send_response(400)
            self._send_default_headers()
            self.end_headers()

    def do_PUT(self):
        if not self._validate():
            return

        content_length = int(self.headers['Content-Length'])

        try:
            data = json.loads(self.rfile.read(content_length).decode('utf-8'))

        except Exception as e:
            traceback.print_exc()
            self._send_error('Received invalid json')
            return

        try:
            resp = self._mpr.call(url=self.path, method='PUT',
                args={'headers': self.headers, 'payload': data})

        except Exception as e:
            traceback.print_exc()
            self._send_error(e)
            return

        if resp:
            self._handle_mapper_response(resp)
            self.send_response(self._status_code, self._message)

        else:
            self.send_response(400)

        self._send_default_headers()
        self.end_headers()

    def do_DELETE(self):
        if not self._validate():
            return

        try:
            resp = self._mpr.call(url=self.path, method='DELETE',
                args={'headers': self.headers})

        except Exception as e:
            traceback.print_exc()
            self._send_error(e)
            return

        if resp:
            self._handle_mapper_response(resp)
            self.send_response(self._status_code, self._message)

        else:
            self.send_response(400)

        self._send_default_headers()
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_default_headers()
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def _serialize(self, obj):
        if isinstance(obj, datetime.datetime):
            serial = obj.isoformat()

        return serial

    def _validate(self):
        if not validator:
            return True

        if validator_excludes:
            if self.path in validator_excludes:
                return True

        try:
            valid = validator(self.path, self.headers)

        except Exception as e:
            traceback.print_exc()
            self._send_error(e)
            return False

        if not valid:
            self.send_response(401)
            self._send_default_headers()
            self.end_headers()

            return False

        return True

    def _get_cookies(self):
        cookie = self.headers.get('Cookie')
        if not cookie:
            return None

        return cookies.BaseCookie(cookie)

    def _handle_mapper_response(self, response):
        self._status_code = response['status_code']
        self._message     = response['message']     if 'message' in response else ''
        self._cookie      = response['cookie']      if 'cookie'  in response else None
        self._payload     = response['payload']     if 'payload' in response else None

    def _send_error(self, error_message):
        self.send_response(500, error_message)
        self.send_header('Content-type', 'text/plain')
        self._send_default_headers()
        self.end_headers()

    def _send_default_headers(self):
        if 'Origin' in self.headers:
            self.send_header('Access-Control-Allow-Origin', self.headers['Origin'])
        else:
            self.send_header('Access-Control-Allow-Origin', '*')

        self.send_header('Access-Control-Allow-Credentials', 'true')

class Config(object):
    """Config to be passed to the Server"""

    address                = '0.0.0.0'
    port                   = 8088
    validate_callback      = None
    validate_exclude_paths = None

class Server(server.HTTPServer):
    def __init__(self, conf):
        """Constructor to initialize the server

        Args:
            conf (Config): configuration for this server instance
        """
        if conf.validate_callback:
            global validator
            validator = conf.validate_callback

        if conf.validate_exclude_paths:
            global validator_excludes
            validator_excludes = conf.validate_exclude_paths

        super(Server, self).__init__((conf.address, conf.port), _RequestHandler)
