# coding=utf8
from flask import Flask, request, abort
import logging
from common.logutil import Log

import requests
import json
import time

import sys
sys.path.append('../kg_qq')

from kg_qq import get_info_ks, get_info_kg, get_info_weizhang
#from flask_test.kg_qq import get_info_ks, get_info_kg, get_info_weizhang

from wechatpy import parse_message
from wechatpy.utils import check_signature
from wechatpy.replies import create_reply, ArticlesReply, ImageReply
from wechatpy.enterprise.crypto import WeChatCrypto
from wechatpy.exceptions import InvalidSignatureException
from wechatpy.events import SubscribeEvent
from wechatpy.client.api.media import WeChatMedia

TOKEN='cl66'
CorpId='wxe6a9684e18834fcd'
EncodingAESKey='DkwkHgwUStoLmaoBhQfO2hOaVIdfbdpa9kpq2xBfOHB'

wechat_logger = Log('wechat', log_path='logs/wechat.log', log_level=logging.INFO).log


app = Flask(__name__)

@app.route('/', methods=['GET'])
def hello_world():
    try:
        signature = request.args.get('signature', None)
        timestamp = request.args.get('timestamp', None)
        nonce = request.args.get('nonce')

        check_signature(TOKEN, signature, timestamp, nonce)

        wechat_logger.info('request.args is %s' % request.args)

        crypto = WeChatCrypto(TOKEN, EncodingAESKey, CorpId)
        echo_str = request.args.get('echostr', '')
        try:
            echo_str = crypto.check_signature(
                signature,
                timestamp,
                nonce,
                echo_str
            )
        except InvalidSignatureException:
            abort(403)
        return echo_str
    except:
        return 'error'



@app.route('/', methods=['POST'])
def wechat():
    xml = request.stream.read()
    msg = parse_message(xml)
    print(msg)

    if msg.type == 'event':
        if isinstance(msg, SubscribeEvent):
            reply = subscribeevent_handle(msg)
        else:
            reply = create_reply('暂不支持其它事件', message=msg)
    elif msg.type == 'text':
        reply = text_handler(msg, msg.content)
    elif msg.type == 'image':
        reply = create_reply('图片好好哟', message=msg)
    elif msg.type == 'voice':
        reply = text_handler(msg, msg.recognition)
    elif msg.type == 'video':
        reply = create_reply('视频挺不错哟', message=msg)
    # elif msg.type in ['location','link']:
    #     pass
    else:
        reply = create_reply('暂不支持处理link和location', message=msg)

    # 转换成 XML
    xml = reply.render()
    return xml

def subscribeevent_handle(msg):
    reply = create_reply('欢迎关注，直接回复全民K歌或快手的网址，用来获取真实播放地址\n回复"违章"或"限号"可查询相关信息！', message=msg)
    return reply

def text_handler(msg, Content):
    if not Content:
        reply = create_reply('啥都没有输入啊！', message=msg)
        return reply
    if Content.startswith('http'):

        if 'www.kuaishou.com' in Content:
            playurl, title, image = get_info_ks(Content)
        elif 'kg.qq.com' in Content:
            playurl, title, image = get_info_kg(Content)
        else:
            playurl = ''
            title = u'目前暂不提供非快手及全民K歌来源外的播放地址解析！'
            image = 'http://qq.yh31.com/tp/zjbq/201612311842344128.gif'

        reply = ArticlesReply(message=msg, articles=[
            {
                'title': title,
                'description': title,
                'url': playurl,
                'image': image,
            },
        ])
    elif u'违章' in Content:
        reply = weizhang(msg)
    elif u'限号' in Content or u'限行' in Content:
        reply = xianhao(msg)
    else:
        reply = tuling_Ai(msg, Content)
        #reply = create_reply('不是网址', message=msg)

    return reply

def weizhang(msg):
    reply = ArticlesReply(message=msg, articles=[
        {
            'title': u'全国违章查询',
            'description': u'查询全国违章，方便',
            'url': 'http://m.cheshouye.com/api/weizhang/?dp=14&dc=189',
            'image': 'http://img02.tooopen.com/images/20160614/tooopen_sy_165048289591.jpg',
        },
    ])
    return reply


def xianhao(msg):
    with open('xianhao.txt', 'r') as rf:
        data = eval(rf.readlines()[0].strip()) #{'weeks':'18','image_url':'1231'}
        weeks = int(data.get('weeks'))
        weeks_now = int(time.strftime("%W"))
        if weeks_now > weeks:
            url = 'http://www.bjjtgl.gov.cn/zhuanti/10weihao/'
            image = get_info_weizhang(url)

            if image:
                image = image[0]
                data['weeks'] = weeks_now
                data['image'] = image

                with open('xianhao.txt', 'a') as wf:
                    wf.write(json.dumps(weeks))
            else:
                image = data.get('image')
        else:
            image = data.get('image')

    reply = ArticlesReply(message=msg, articles=[
        {
            'title': u'北京限号',
            'description': u'北京限号信息',
            'url': 'http://www.bjjtgl.gov.cn/zhuanti/10weihao/index.html',
            'image': image,
        },
    ])
    return reply


def tuling_Ai(msg, text):
    url = 'http://openapi.tuling123.com/openapi/api/v2'
    key = 'e4be290b52a94f6ab2667cae5eca7e71'

    input_data = {}
    input_data['perception'] = {}
    input_data['userInfo'] = {"apiKey": key, 'userId':1}
    input_data['perception']['inputText'] = {"text": text}
    input_data['perception']['selfInfo'] = ''

    r = requests.post(url, data=str(json.dumps(input_data)))

    data = json.loads(r.text)
    code = data.get('intent').get('code')
    reply = create_reply(u'出错啦，请重试', message=msg)
    if code > 10000:
        result = data.get('results')
        for res in result:
            resultType = res.get('resultType')
            if resultType == 'text':
                values = res.get('values').get('text')
                reply = create_reply(values, message=msg)
    return reply



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
    #msg=u'北京天气'
    # tuling_Ai(msg)
    #print(xianhao(msg))
