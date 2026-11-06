"""Check a running Kittygram through its gateway using only the stdlib."""

import base64
import json
import os
import re
import secrets
import struct
import urllib.request
import zlib

BASE_URL = os.getenv('KITTYGRAM_URL', 'http://127.0.0.1:9000').rstrip('/')


def request(path, data=None, token=None, method=None):
    headers = {}
    if token:
        headers['Authorization'] = f'Token {token}'
    if data is not None:
        headers['Content-Type'] = 'application/json'
        data = json.dumps(data).encode()
    req = urllib.request.Request(
        BASE_URL + path, data=data, headers=headers, method=method,
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        return response.status, response.read(), response.headers


def png_chunk(kind, data):
    return (struct.pack('!I', len(data)) + kind + data
            + struct.pack('!I', zlib.crc32(kind + data)))


def main():
    status, html, _ = request('/')
    assert status == 200 and b'Kittygram' in html
    js_path = re.search(rb'src="(/static/js/[^\"]+)"', html).group(1)
    status, javascript, headers = request(js_path.decode())
    assert status == 200 and len(javascript) > 1000
    assert 'javascript' in headers['Content-Type']
    status, css, headers = request('/static/admin/css/base.css')
    assert status == 200 and 'text/css' in headers['Content-Type']
    assert len(css) > 100
    assert request('/admin/login/')[0] == 200
    assert request('/sign-in')[0] == 200
    print('Frontend, SPA routes, JavaScript and admin static: OK')

    password = secrets.token_urlsafe(24)
    credentials = {'username': 'smoke_' + secrets.token_hex(6),
                   'password': password}
    assert request('/api/users/', credentials)[0] == 201
    login = json.loads(request('/api/token/login/', credentials)[1])
    token = login['auth_token']
    cat_id = None
    try:
        png = (b'\x89PNG\r\n\x1a\n'
               + png_chunk(b'IHDR', struct.pack('!2I5B', 1, 1, 8, 2, 0, 0, 0))
               + png_chunk(b'IDAT', zlib.compress(b'\0\xff\0\0'))
               + png_chunk(b'IEND', b''))
        data = {
            'name': 'Smoke test', 'color': '#FFA500', 'birth_year': 2024,
            'image': 'data:image/png;base64,' + base64.b64encode(png).decode(),
        }
        status, body, _ = request('/api/cats/', data, token)
        assert status == 201
        cat = json.loads(body)
        cat_id = cat['id']
        image_path = cat['image_url']
        assert image_path.startswith('/media/')
        status, image, headers = request(image_path)
        assert status == 200 and image.startswith(b'\x89PNG')
        assert headers['Content-Type'] == 'image/png'
        status, body, _ = request(f'/api/cats/{cat_id}/', token=token)
        assert status == 200 and json.loads(body)['name'] == 'Smoke test'
        print('Registration, login, PostgreSQL write/read and media: OK')
    finally:
        if cat_id is not None:
            assert request(f'/api/cats/{cat_id}/', token=token,
                           method='DELETE')[0] == 204
        assert request('/api/users/me/', {'current_password': password},
                       token, 'DELETE')[0] == 204
    print('Test user and cat removed. Smoke test passed.')


if __name__ == '__main__':
    main()
