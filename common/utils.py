#!/usr/bin/python
# coding=utf-8
__author__ = 'clhou@oklantu.com'

import gzip
import json
import logging
import os
import re
import smtplib
import sys
import StringIO
import time
import traceback
import urllib2
from ConfigParser import ConfigParser
from datetime import timedelta
from email.mime.text import MIMEText
from lxml import etree
from pymongo import MongoClient



def get_mongo_client(cfg_path='/config/mongo.config'):
  parser = ConfigParser()
  parser.read(os.path.dirname(os.path.realpath(__file__)) + cfg_path)
  host = parser.get('mongo_crawler', 'host')
  user = parser.get('mongo_crawler', 'user')
  password = parser.get('mongo_crawler', 'passwd')
  mongo_client = MongoClient(host)
  mongo_client.admin.authenticate(user, password)
  return mongo_client


def convert_map_regs(regmap):
  res = {}
  for domain, reglist in regmap.iteritems():
    regs = []
    for r in reglist:
      regs.append(re.compile(r, re.IGNORECASE))
    if regs:
      res[domain] = regs
  return res


def send_mail(from_address, to_address, subject, message, headers=None, **kw):
  subtype = kw.get('subtype', 'plain')
  charset = kw.get('charset', 'utf-8')
  msg = MIMEText(message, subtype, charset)
  msg['Subject'] = subject
  msg['From'] = from_address
  msg['To'] = ','.join(to_address)
  try:
    server = smtplib.SMTP('mail.letv.com')
    server.sendmail(from_address, to_address, msg.as_string())
    server.quit()
    return True
  except:
    logging.exception('failed to send mail, from: [%s], to: [%s], message: [%s]',
                      from_address, to_address, message)
    return False


def list2dict(data):
  dic = {}
  for idx, value in enumerate(data):
    dic[str(idx)] = value
  return dic


def reverse_kv(dic):
  if not dic:
    return dic
  result = {}
  for k, v in dic.items():
    result[v] = k
  return result


def gen_thrift_fields(thrift_cls):
  data = {}
  for x in thrift_cls.thrift_spec:
    if x:
      data[x[2]] = (x[1], x[3])
  return data




def str_unzip(buf):
  f = gzip.GzipFile(fileobj = StringIO.StringIO(buf), mode = 'rb')
  html = f.read()
  f.close()
  return html


def str_gzip(content):
  buf = StringIO.StringIO()
  f = gzip.GzipFile(mode = 'wb', fileobj = buf)
  f.write(content)
  f.close()
  return buf.getvalue()


def FetchHTML(url, timeout=30, header={}, data=None, check_redirect=False):
  if not url:
    return (None, None) if check_redirect else None
  for i in range(2):
    ret = _fetch_html(url, timeout, True, header, data, check_redirect)
    if ret:
      return ret
    time.sleep(1)
  logging.error('failed to get html of url, %s', url)
  return (None, None) if check_redirect else None


def fetch_html_by_post(url, values, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'}, timeout=20):
  def _fetch_html_by_post(url, values, headers, timeout):
    #data = urllib.urlencode(values)
    data = values
    req = urllib2.Request(url, data, headers, timeout)
    response = urllib2.urlopen(req)
    result = response.read()
    return result

  if not url:
    return None
  for i in range(2):
    result = _fetch_html_by_post(url, values, headers, timeout)
    if result:
      return result
  logging.error('failed to get htm of url by post, %s', url)
  return None


def get_charset(s):
  s = s.replace(" ", "").lower()
  index = s.find("charset=")
  if index != -1:
    s = s[index + len("charset="):]
    index = s.find(">")
    if index != -1:
      s = s[:index]
    s = s.strip("\",; /")
    return s


def _fetch_html(url, timeout, check_charset=True, header={}, post_data=None, check_redirect=False):
  try:
    req = urllib2.Request(url)
    ua = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.153'
    req.add_header("User-Agent", ua)

    if isinstance(header, dict):
      req.headers.update(header)
    f = urllib2.urlopen(req, data=post_data, timeout=timeout)
    encoding = None
    if "content-encoding" in f.info().dict:
      encoding = f.info().dict["content-encoding"]
    if encoding and encoding != "gzip":
      logging.warning("invalid compress encoding [%s] for url [%s]" % (encoding, url))
      return (None, None) if check_redirect else None
    html = f.read()
    if encoding:
      html = Decompress(html)

    charset = None
    if "content-type" in f.info().dict:
      charset = get_charset(f.info().dict["content-type"])
    if charset is None and check_charset:
      charset = GetCharset(html)
    if charset not in [None, 'utf8', 'utf-8']:
      html = html.decode(charset, "ignore").encode('utf8')
    return (html, f.url) if check_redirect and html else html
  except:
    logging.exception("failed to get html, %s", url)
    return (None, None) if check_redirect else None



def Decompress(buf):
  f = gzip.GzipFile(fileobj=StringIO.StringIO(buf), mode='rb')
  html = f.read()
  f.close()
  return html


def GetCharset(html):
  charset = None
  rules = ["substring-after(/html/head/meta"
           "[contains(@content, 'charset')]/@content, 'charset=')",
           "/html/head/meta/@charset"]
  try:
    for rule in rules:
      datas = etree.HTML(html).xpath(rule)
      if isinstance(datas, str) and len(datas) > 0:
        charset = datas
      elif isinstance(datas, list) and len(datas) > 0 and len(datas[0]) > 0:
        charset = datas[0]
      else:
        continue
      break
  except:
    logging.exception('failed to retrieve charset info')
    return None
  return charset


def fetch_json_result(api_str, regex='({.*})', timeout=30, header={}, data=None, replace=False):
  try:
    json_data = re.search(regex, FetchHTML(api_str, timeout=timeout, header=header, data=data)).group(1)
    if replace:
      json_data = json_data.replace('\\', '')
    return json.loads(json_data)

  except:
    logging.exception('Failed load json via api. %s', api_str)
    return None


def atoi(num_str):
  if num_str is None:
    return None
  if isinstance(num_str, (int, float, long)):
    return num_str
  if not isinstance(num_str, basestring):
    return None
  try:
    return int(num_str)
  except:
    pass

  try:
    num_str = num_str if isinstance(num_str, unicode) \
      else num_str.decode('utf-8', 'ignore')
    num_str = erase_all(num_str, [',', u'，', ' '])
    digit_list = [unicode(i) for i in range(0, 10)]
    digit_list.append(u'.')
    multiple = {u'亿': 100000000, u'万': 10000, u'千': 1000, u'K': 1000, u'k': 1000, u'百': 100, u'十': 10}
    digit_map = {}
    for k, v in zip(list(u'零一二三四五六七八九'), range(0, 10)):
      digit_map[k] = str(v)
    result = 0
    result_int = 0
    clip_num = ''
    clip_decimal = None
    skip_multiple = False
    num_len = len(num_str)
    for idx, char in enumerate(num_str):
      if char == u'.' or char == u'点':
        skip_multiple = False
        clip_decimal = ''
        if idx < num_len - 1:
          continue
      if char in digit_list or char in digit_map:
        skip_multiple = False
        char = digit_map[char] if char in digit_map else char
        if clip_decimal is None:
          clip_num += char
        else:
          clip_decimal += char
        if idx < num_len - 1:
          continue
      elif char not in multiple and char not in digit_list:
        return None
      if skip_multiple:
        continue
      factor = 1
      while idx < num_len and num_str[idx] in multiple:
        factor *= multiple[num_str[idx]]
        idx += 1
        skip_multiple = True
      clip_num = '0' if not clip_num else clip_num
      clip_decimal = '0' if not clip_decimal else clip_decimal
      result += int(clip_num) * factor + \
                int(clip_decimal) * factor * 1.0 / (10 ** len(clip_decimal))
      clip_decimal = None
      clip_num = ''
      result_int = int(result)
    return result_int if result_int == result else result
  except:
    logging.exception('failed to parse string to int/float, %s', num_str)
    return None


def erase_all(string, erase_list, from_idx=0):
  clip = reduce(lambda x, y: x.replace(y, ''), erase_list, string)
  return clip if not from_idx else string[:from_idx] + clip



black_regs = ['http://list.iqiyi.com/www/13/',
              'http://list.iqiyi.com/www/21/',
              'http://list.iqiyi.com/www/8/',
              'http://list.iqiyi.com/www/20',
              'http://list.iqiyi.com/www/29/',
              'http://list.iqiyi.com/www/5/',
              'http://list.iqiyi.com/www/16/',
              'http://list.iqiyi.com/www/\d+/\d*-\d*-\d{4}.*.html',
              'http://v.qq.com/mvlist',
              'http://v.qq.com/fashion',
              'http://v.qq.com/baby',
              ]


def update_hot_urls(mongo_col, url, doc_type, fresh_frequency, is_recall=False):
  if not is_recall:
    for reg in black_regs:
      if re.search(reg, url):
        return
  next_recall_time = int(time.time()) + fresh_frequency
  mongo_col.update(
      {'url': url},
      {'$set': {'url': url, 'doc_type': doc_type, 'fresh_frequency': fresh_frequency,
        'next_recall_time': next_recall_time, 'update_time': time.strftime('%Y%m%d_%H%M%S')}},
      upsert=True)



def encode_item(obj):
  try:
    if isinstance(obj, tuple):
      pass
    elif isinstance(obj, unicode):
      obj = obj.encode('utf-8')
    elif isinstance(obj, dict):
      for k, v in obj.items():
        obj[encode_item(k)] = encode_item(v)
    elif hasattr(obj, '__iter__'):
      for idx, v in enumerate(obj):
        obj[idx] = encode_item(v)
    elif hasattr(obj, "__dict__"):
      for key, value in obj.__dict__.iteritems():
        if not callable(value):
          setattr(obj, key, encode_item(value))
    return obj
  except:
    logging.exception('failed encode item, type: %s, %s', type(obj), obj)


def str2dict(s):
  dic = {}
  if not s:
    return dic
  for item in s.split(';'):
    k, v = item.split('|')
    dic[k] = v
  return dic


def dict2str(dic):
  if not dic:
    return None
  s = []
  for k, v in dic.items():
    s.append(str(k) + '|' + str(v))
  return ';'.join(s)


def drop_noise(data, noise_list, splitter=';'):
  attrs = set(data.split(splitter))
  for token in noise_list:
    if token in attrs:
      attrs.remove(token)
  return splitter.join(list(attrs)).strip(splitter)


def safe_eval(input_str):
  if not input_str:
    return None
  try:
    return eval(input_str, {"__builtins__": None},
                {'false': False, 'true': True, 'null': None})
  except:
    sys.stderr.write(traceback.format_exc())
    return None


def obj2dict(obj):
  if isinstance(obj, dict):
    data = {}
    for (k, v) in obj.items():
      data[k] = obj2dict(v)
    return data
  elif hasattr(obj, "_ast"):
    return obj2dict(obj._ast())
  elif hasattr(obj, "__iter__"):
    return [obj2dict(v) for v in obj]
  elif hasattr(obj, "__dict__"):
    data = dict([(key, obj2dict(value)) for key, value in obj.__dict__.iteritems()
                 if not callable(value) and not key.startswith('_')])
    return data
  else:
    return obj


def get_slope(i, j, p_list):
  dy = float(p_list[j][1] - p_list[i][1])
  dx = p_list[j][0] - p_list[i][0]
  return dy / dx


def compress_play_trends(dict_trends):
  if not dict_trends:
    return None

  list_trends = sorted(dict_trends.iteritems(), key=lambda t: t[0])
  if len(list_trends) < 3:
    return list_trends

  # check trends' value
  trends = [list_trends[0]]
  v = list_trends[0][1]
  for i in range(1, len(list_trends)-1):
    if list_trends[i][1] > v:
      trends.append(list_trends[i])
      v = list_trends[i][1]
  if trends[-1][0] != list_trends[-1][0]:
    trends.append(list_trends[-1])

  if len(trends) < 10:
    return trends

  import math
  # smooth the trends curve
  diff_range = math.tan(math.radians(5)) # 5/360 degree difference
  cur_i = 0
  list_trends = [trends[0]]
  if not trends[0][1]:
    list_trends.append(trends[1])
    cur_i = 1
  cur_slope = get_slope(cur_i, cur_i+1, trends)
  for i in range(cur_i+2, len(trends)-1):
    slope = get_slope(cur_i, i, trends)
    if math.fabs(slope - cur_slope) > diff_range:
      list_trends.append(trends[i-1])
      cur_i = i - 1
      cur_slope = get_slope(i-1, i, trends)
  list_trends.append(trends[-1]) # add the last point
  return list_trends


def print_object(video):
    # logging.info('-' * 40)
    print '-' * 40
    for k, v in sorted(video.__dict__.iteritems()):
      if not v:
        continue
      #if k == 'crawl_history':
        #v = len(v.crawl_history)
      #el
      if k == 'play_trends':
        v = len(v.split(';'))
      # logging.info('%-20s -> %s', k, v)
      print '%-20s -> %s' % (k, v)
    # logging.info('-' * 40)
    print '-' * 40


def load_start_urls(path):
  data = []
  for filename in os.listdir(path):
    filepath = os.path.join(path, filename)
    if os.path.isfile(filepath):
      with open(filepath) as f:
        try:
          data.extend(json.load(f))
        except:
          logging.exception('failed to load json from file, %s', filepath)
          raise
  result = {}
  for item in data:
    if item.get("enable") == False:
      continue
    urls = item.pop('url')
    for url in urls:
      result[url] = item
  return result

def cal_priority(doc):
  return doc.doc_type

def cycle_run(func, seconds=60, times=-1, logger=None):
  # times = -1 -> infinite times
  assert seconds > 0 and times > -2
  if not times:
    return
  logger = logger if logger else logging
  while 1:
    stamp = time.time()
    func()
    used_time = time.time() - stamp

    logger.info('=' * 100)
    msg = 'Job lasts: %s' % timedelta(seconds=int(used_time))
    len_space = (96 - len(msg)) / 2
    logger.info('|*%s%s%s*|', ' ' * len_space, msg, ' ' * (96 - len(msg) - len_space))
    logger.info('=' * 100)

    spare = seconds - used_time
    if spare > 0:
      time.sleep(spare)
    if times == -1:
      continue
    times -= 1
    if not times:
      break

def first(iterable, default=None, key=None):
  """
  Return first element of `iterable` that evaluates true, else return None
  (or an optional default value).
  >>> first([0, False, None, [], (), 42])
  42
  >>> first([0, False, None, [], ()]) is None
  True
  >>> first([0, False, None, [], ()], default='ohai')
  'ohai'
  >>> import re
  >>> m = first(re.match(regex, 'abc') for regex in ['b.*', 'a(.*)'])
  >>> m.group(1)
  'bc'
  The optional `key` argument specifies a one-argument predicate function
  like that used for `filter()`.  The `key` argument, if supplied, must be
  in keyword form.  For example:
  >>> first([1, 1, 3, 4, 5], key=lambda x: x % 2 == 0)
  4
  """
  if key is None:
    for el in iterable:
      if el:
        return el
  else:
    for el in iterable:
      if key(el):
        return el
  return default

