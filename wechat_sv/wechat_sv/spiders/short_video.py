#coding=utf-8

__author__ = 'clhou@oklantu.com'

import time
import json
from scrapy.spider import BaseSpider
import scrapy

from wechat_sv.common.domain_parser import query_domain_from_url
from wechat_sv.items import WechatSvItem


class Short_VideoSpider(BaseSpider):
    name = "sv"

    start_urls = [
        "https://www.kuaishou.com/photo/216124509/2140526600"
    ]

    def parse(self, response):
        #print(response.body)
        item = WechatSvItem()

        # if 'www.kuaishou.com' in response.url:
        #     pass

        item["stream"], item["title"], item["image"], urls = get_info_ks(response.url, response.body)

        item["source"] = query_domain_from_url(response.url)

        item["createtime"] = int(time.time())
        item["url"] = response.url

        yield item

        for url in urls:
            print(url)

            yield scrapy.Request(url,
                                 callback=self.parse,
                                 )


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