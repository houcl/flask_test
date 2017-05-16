# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
from pymongo import MongoClient
import json
from common.utils import get_mongo_client

class WechatSvPipeline(object):
    def process_item(self, item, spider):
        if not item:
            return None
        mongo_client = get_mongo_client('/config/mongo.config')
        db = mongo_client.wechat
        #print(type(json.dumps(item)))
        db.short_video.insert(dict(item))

        return item
