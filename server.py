from gevent import monkey
monkey.patch_all()

import subprocess
import os
import shutil
import requests
import time
import random
import hashlib
import urllib

from flask import Flask, request, redirect, make_response, send_from_directory, render_template

from flask.ext.socketio import SocketIO, emit, join_room, leave_room, \
    close_room, disconnect

app = Flask(__name__)
app.debug = True

socketio = SocketIO(app)


from functools import wraps, update_wrapper
from datetime import datetime

backgrounds_dir = '/home/alexcb/background_fucker/backgrounds'


@socketio.on('connect', namespace='/test')
def test_connect():
    pass


@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    pass


def update_clients_with_new_background():
    socketio.emit('backgroundchange',
                  {'background': get_current_background_url()},
                  namespace='/test')


@app.route('/')
def index():
    return render_template('index.html', background_url=get_current_background_url())


@app.route('/background')
def background():
    return render_template('background.html', background_url=get_current_background_url())


cache = {}
def get_md5_sum(path):
    try:
        return cache[path]
    except KeyError:
        cache[path] = hashlib.md5(open(path, 'rb').read()).hexdigest()
    return cache[path]


    socketio.emit('my response',
                  {'data': 'Server generated event', 'count': -1},
                  namespace='/test')


def get_redirect_url(username='unknown'):
    url = '/'
    return url


def get_name_from_ip(ip_addr):
    return {
            'X.X.X.X': 'USERNAME',
            }.get(ip_addr, 'Unknown')


def nocache(view):
    @wraps(view)
    def no_cache(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Last-Modified'] = datetime.now()
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response
        
    return update_wrapper(no_cache, view)


def get_current_background_url():
    return '/backgrounds/' + get_backgrounds()[-1]


def get_backgrounds():
    return sorted([x for x in os.listdir(backgrounds_dir) if x.startswith('communal_background_')])


def get_unique_backgrounds():
    seen = set()
    backgrounds = []
    for x in get_backgrounds():
        hashsum = get_md5_sum(os.path.join(backgrounds_dir, x))
        if hashsum not in seen:
            seen.add(hashsum)
            backgrounds.append(x)
    return backgrounds


@app.route('/archive/<int:page>')
def archive(page):
    num_per_page=50
    start = page*num_per_page
    end = start + num_per_page
    backgrounds = list(reversed(get_unique_backgrounds()))
    images = ''.join('<a href="/backgrounds/%(url)s"><img src="/backgrounds/%(url)s" height=300></a>' % {'url': x} for x in backgrounds[start:end])
    links = '<center>'
    if page > 0:
        links += '<a href="/archive/%s">Newest</a> ' % (0,) 
        links += '<a href="/archive/%s">Newer</a> ' % (page - 1,) 
    else:
        links += 'Newest '
        links += 'Newer '

    links += '&nbsp;&nbsp;Displaying %s - %s&nbsp;&nbsp;' % (start+1, end)

    links += ' <a href="/archive/%s">Older</a>' % (page + 1,) 
    links += ' <a href="/archive/%s">Oldest</a>' % (len(backgrounds)/num_per_page,) 

    links += '</center>'

    return '<hr>'.join(('<a href="/">HOME</a>', links, images, links))


@app.route('/backgrounds/<path:path>')
def send_background_image(path):
    return send_from_directory(backgrounds_dir, path)


@app.route('/desktop', methods = ['POST'])
def change_background():
    background_url = request.form['background']

    try:
        username = get_name_from_ip(request.remote_addr)
        print '%s (%s) is setting background to %s' % (username, request.remote_addr, background_url)
        background = requests.get(background_url)
        background.raise_for_status()
        if background.headers['content-type'].split('/')[0] != 'image':
            return 'URL %s returned content-type: %s which is not an image' % (
                background_url, background.headers['content-type'])

        background_filename = 'communal_background_%s_%s.jpg' % (int(time.time()), request.remote_addr)
        background_path = os.path.join(backgrounds_dir, background_filename)
        background_path = os.path.abspath(background_path)
        print 'Setting background to %s' % background_path
        with open(background_path, 'wb') as fp:
            fp.write(background.content)
        subprocess.check_call(['/home/alexcb/bin/change_background', background_path])
        update_clients_with_new_background()
    except Exception as e:
        return str(e)

    url = get_redirect_url(username)
    print 'Redirecting to %s' % url
    return redirect(url)


if __name__ == '__main__':
    app.run('0.0.0.0')

