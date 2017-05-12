# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class WechatSvItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    title = scrapy.Field()
    stream = scrapy.Field()
    source = scrapy.Field()
    createtime = scrapy.Field()
    showtime = scrapy.Field()
    image = scrapy.Field()
    url = scrapy.Field()
