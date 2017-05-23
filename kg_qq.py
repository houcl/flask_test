# coding=utf-8

__author__ = 'clhou@oklantu.com'

from common.logutil import Log
from flask import Flask, render_template, request
import logging
import json
app = Flask(__name__)


user_dict = {}
super_user = []

server_logger = Log('kg_qq', log_path='logs/kg_qq.log', log_level=logging.INFO).log

@app.route('/')
def hello_world():
    return 'Hello World!'

@app.route('/kg', methods=['GET'])
def kg():
    ip = str(request.remote_addr)
    server_logger.info('user ip is %s come to kg page' % ip)

    if ip in user_dict.keys():
        total = user_dict.get(ip)
        if total >=3:
            server_logger.info('user ip is %s. 已超过授权使用次数，请联系管理员解决！' % ip)
            return render_template('kg_error.html', errorinfo=u'已超过授权使用次数，请联系管理员解决！')
    return render_template('kg_index.html')

@app.route('/kg_result', methods=['POST'])
def kg_result():
    ip = str(request.remote_addr)
    url = request.form['url'].strip()
    server_logger.info('user ip is %s come' % ip)
    server_logger.info('url is %s' % url)
    if not url:
        server_logger.info('%s 输入的url内容为空，请参考样例重新输入！' % ip)
        return render_template('kg_error.html', errorinfo=u'输入的url内容为空，请参考样例重新输入！')
    playurl, title, image = get_info_kg(url)

    if ip in user_dict.keys():
        if ip not in super_user:
            user_dict[ip] = user_dict.get(ip) + 1
            server_logger.info('user ip is %s . it total is %s ' % (ip, user_dict[ip]))
    else:
        user_dict[ip] = 1

    server_logger.info('playurl is %s' % playurl)
    return render_template('kg_result.html', playurl=playurl, url=url)

@app.route('/ks', methods=['GET'])
def ks():
    ip = str(request.remote_addr)
    server_logger.info('user ip is %s come to kg page' % ip)

    if ip in user_dict.keys():
        total = user_dict.get(ip)
        if total >=3:
            server_logger.info('user ip is %s. 已超过授权使用次数，请联系管理员解决！' % ip)
            return render_template('kg_error.html', errorinfo=u'已超过授权使用次数，请联系管理员解决！')
    return render_template('ks_index.html')

@app.route('/ks_result', methods=['POST'])
def ks_result():
    ip = str(request.remote_addr)
    url = request.form['url'].strip()
    server_logger.info('user ip is %s come' % ip)
    server_logger.info('url is %s' % url)
    if not url:
        server_logger.info('%s 输入的url内容为空，请参考样例重新输入！' % ip)
        return render_template('kg_error.html', errorinfo=u'输入的url内容为空，请参考样例重新输入！')
    playurl, title, image = get_info_ks(url)

    if ip in user_dict.keys():
        if ip not in super_user:
            user_dict[ip] = user_dict.get(ip) + 1
            server_logger.info('user ip is %s . it total is %s ' % (ip, user_dict[ip]))
    else:
        user_dict[ip] = 1

    server_logger.info('playurl is %s' % playurl)
    return render_template('ks_result.html', playurl=playurl, url=url)

def base_xpath(url):
    if not url:
        return False
    url = url.strip()

    from common.xpather import Xpather
    from common.utils import FetchHTML

    xpather = Xpather()
    xpather.load_templates('../template')
    #xpather.load_templates('../kg_qq/template')
    html = FetchHTML(url)

    result = xpather.parse(url, html)
    return result

def get_info_ks(url):
    result = base_xpath(url)
    if not result:
        return None
    playurl = result.get('playurl', None)
    title = result.get('title', None)
    image = result.get('image', None)

    if playurl:
        playurl = playurl[0]
    if title:
        title = title[0]
    if image:
        image = image[0]

    return playurl, title, image


def get_info_kg(url):
    result = base_xpath(url)

    if not result:
        return None
    for k, v in result.items():
        playurl, song_name, image = '', '', ''
        if k == 'items':
            v = v[0].lstrip('window.__DATA__ = ')
            v = v.rstrip('; ').encode('utf8')
            v = json.loads(v)

            playurl = v.get("detail", None).get("playurl", None)
            song_name = v.get("detail", None).get("song_name", None)
            image = v.get("detail", None).get("cover", None)
            if not playurl:
                playurl = v.get("detail", None).get("playurl_video", None)
        return playurl, song_name, image

def get_info_weizhang(url):
    result = base_xpath(url)
    if not result:
        return None
    image = result.get('image', None)
    return image

if __name__ == '__main__':
    #app.run(host='0.0.0.0', port=8999)
    url = 'http://kg.qq.com/node/play?s=j4SSz2jWBTM56jXz'
    print(get_info_kg(url))
    # get_info(url)