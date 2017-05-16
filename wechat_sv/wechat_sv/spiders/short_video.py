#coding=utf-8

__author__ = 'clhou@oklantu.com'

import time
import json
from scrapy.spider import BaseSpider
import scrapy
import logging

from wechat_sv.common.domain_parser import query_domain_from_url
from wechat_sv.items import WechatSvItem
from wechat_sv.common.utils import get_mongo_client
from wechat_sv.common.logutil import Log

spider_logger = Log('wechat', log_path='logs/spider.log', log_level=logging.DEBUG).log

class Short_VideoSpider(BaseSpider):
    def __init__(self):
        self.mongo_client = get_mongo_client('/config/mongo.config')
        self.db = self.mongo_client.wechat

    name = "sv"

    start_urls = [
        "https://www.kuaishou.com/photo/216124509/2140526600"
    ]

    def parse(self, response):

        urls = None
        item = WechatSvItem()
        item["source"] = query_domain_from_url(response.url)
        item["createtime"] = int(time.time())
        item["url"] = response.url

        if item["source"] == "kuaishou.com":
            item["stream"], item["title"], item["image"], urls = get_info_ks(response.url, response.body)

        mongo_data = self.db.short_video.find_one({"url":item["url"]})

        if not mongo_data:
            spider_logger.info('new add url is %s' % item["url"])
            yield item
        else:
            spider_logger.info('url: %s have in mongo' % item["url"])


        if urls:
            for url in urls:
                mongo_data = self.db.short_video.find_one({"url": url})
                if not mongo_data:
                    spider_logger.info('next parse url is %s' % item["url"])
                    yield scrapy.Request(url,
                                         callback=self.parse,
                                         )
                else:
                    spider_logger.info('url: %s have in mongo' % url)


def base_xpath(url, html):
    if not url:
        return False
    url = url.strip()

    from wechat_sv.common.xpather import Xpather

    xpather = Xpather()
    xpather.load_templates('../../template')
    #xpather.load_templates('../kg_qq/template')

    result = xpather.parse(url, html)
    return result

def get_info_ks(url, html):
    result = base_xpath(url, html)
    if not result:
        return None
    playurl = result.get('playurl', None)
    title = result.get('title', None)
    image = result.get('image', None)
    items = result.get('items', None)
    urls = []

    if playurl:
        playurl = playurl[0]
    if title:
        title = title[0]
    if image:
        image = image[0]
    if items:
        for item in items:
            urls.append(item.get('url')[0])
    return playurl, title, image, urls


def get_info_kg(url, html):
    result = base_xpath(url, html)

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
        return playurl, song_name, image