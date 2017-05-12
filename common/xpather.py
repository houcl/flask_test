#!/usr/bin/python
#
__author__ = 'clhou@oklantu.com'

"""One-line documentation for xpather module.

A detailed description of xpather.
"""


from lxml import etree
from urllib import urlopen
from datetime import datetime
import HTMLParser
import logging
import re
import os
from logutil import Log

temp_logger = Log('template', log_path='logs/template.log', log_level=logging.INFO).log


class RuleItem(object):
  def __init__(self, text, attr):
    self._text = text
    self._attr = attr

  def process(self, datas):
    raise NotImplementedError

class XpathRule(RuleItem):
  def process(self, tree):
    datas = tree.xpath(self._text)
    return [data.strip() for data in datas]

class RegRule(RuleItem):
  def process(self, datas):
    connector = self._attr.get('connector', '')
    power = self._attr.get('power', None)
    none_marker = self._attr.get('none_marker', None)
    pattern = re.compile(self._text, re.U|re.S)
    parsed_result = []
    for data in datas:
      match_result = pattern.match(data)
      if match_result:
        if power is None:
          parsed_result.append(connector.join([group for group in match_result.groups() if group]))
        else:
          s = 0
          for num in match_result.groups():
            s *= int(power)
            s += int(num)
          parsed_result.append(str(s))

      elif none_marker:
        parsed_result.append(none_marker)
        # logging.warning("regex is not match, reg: %s, data: %s, mark as %s" % (self._text, data, none_marker))
      else:
        # logging.warning("regex is not match, reg: %s, data: %s" % (self._text, data))
        continue
    return parsed_result

class PrefixRule(RuleItem):
  def process(self, datas):
    result = []
    dup_flag = self._attr.get('no_duplicate', None)
    for data in datas:
      result.append(data if dup_flag and str(data).startswith(self._text)
                    else self._text + data)
    return result

class SuffixRule(RuleItem):
  def process(self, datas):
    result = []
    for data in datas:
      result.append(data + self._text)
    return result

class SplitRule(RuleItem):
  def process(self, datas):
    result = []
    index = int(self._attr.get('index', '-1'))
    skip_pattern = self._attr.get('not_start_with', None)
    for data in datas:
      slices = data.split(self._text)
      if skip_pattern:
        slices = [item for item in slices if not item.startswith(skip_pattern)]
      if len(slices) <= index:
        continue
      result.extend(slices if index is -1 else [slices[index]])
    return result

class ConnectRule(RuleItem):
  def process(self, datas):
    if len(datas) == 0:
      return []
    self._text = '' if self._text is None else self._text
    return [self._text.join(datas)]

class FormatRule(RuleItem):
  def process(self, datas):
    return [self._text % data for data in datas]

class DropEmptyRule(RuleItem):
  def process(self, datas):
    return [data for data in datas if data]

class UnescapeRule(RuleItem):
  def process(self, datas):
    parser = HTMLParser.HTMLParser()
    return [parser.unescape(data) for data in datas]

class StripRule(RuleItem):
  def process(self, datas):
    return [item.strip(self._text) for item in datas if item]

class MappingRule(RuleItem):
  def process(self, datas):
    srcValue = self._text
    destValue = self._attr.get('map2', None)
    if destValue is None:
      raise Exception("mapping rule must has map2 attr.")
    for i, data in enumerate(datas):
      if data == srcValue:
        datas[i] = destValue
    return datas

rule_map = {'xpath': XpathRule,
            'regex': RegRule,
            'prefix': PrefixRule,
            'suffix': SuffixRule,
            'split': SplitRule,
            'connect': ConnectRule,
            'format': FormatRule,
            'drop_empty': DropEmptyRule,
            'unescape': UnescapeRule,
            'strip': StripRule,
	    'mapping': MappingRule}

class NodeItem(object):
  def __init__(self, target, attr):
    self._target = target
    self._attr = attr

  def _load_from_elem(self, elem, targets=None):
    pass

  def load_from_elem(self, elem, targets=None):
    return self._load_from_elem(elem, targets)

  def _conv_data(self, data, data_type, time_format):
    try:
      if data_type == 'str':
        return data.strip()
      elif data_type == 'int':
        return int(data)
      elif data_type == "float":
        return float(data)
      elif data_type == "datetime":
        return datetime.strptime(
            data.encode('utf8'), time_format.encode('utf8'))
    except ValueError:
      #logging.exception('Error occurred when converting data.')
      return None

  def _conv_data_list(self, datas):
    data_type = self._attr.get('data_type', 'str')
    time_format = self._attr.get('time_format', u'')
    if data_type == 'datetime' and time_format == '':
      logging.error('time_format can not be empty when data_type is time')
      return None

    result = []
    for data in datas:
      conv = self._conv_data(data, data_type, time_format)
      if conv is not None:
        result.append(conv)
    limit = int(self._attr.get('limit', '-1'))
    return result if limit == -1 else result[:limit]

class MatchNode(NodeItem):
  def __init__(self, target, attr):
    NodeItem.__init__(self, target, attr)
    self._rules = []

  def _load_from_elem(self, elem, targets=None):
    children = elem.getchildren()
    if not children:
      return False
    if children[0].tag != 'xpath':
      raise Exception('The fist rule must be xpath, now is %s' % children[0].tag)
    for child in children:
      if child.tag not in rule_map:
        raise Exception('unknown rule name: %s' % child.tag)
      self._rules.append(rule_map[child.tag](child.text, child.attrib))
    return True

  def process(self, tree):
    data = []
    for rule in self._rules:
      if isinstance(rule, XpathRule):
        if tree is None:
          continue
        data.extend(rule.process(tree))
      else:
        data = rule.process(data)
    data = self._conv_data_list(data)
    if not data:
      return None
    return {self._target: data}

  def show_info(self):
    logging.debug('match')
    for rule in self._rules:
      logging.debug(type(rule))

class StructNode(NodeItem):
  def __init__(self, target, attr):
    NodeItem.__init__(self, target, attr)
    self._xpath = []
    self._subnodes = []

  def _load_from_elem(self, elem, targets=None):
    children = elem.getchildren()
    if not children:
      return False
    while children[0].tag == 'xpath':
      self._xpath.append(children.pop(0).text)

    for child in children:
      target = child.get('target', None)
      if not target:
        raise Exception('node must has target attribute')
      if child.tag == 'match':
        if targets and target not in targets:
          continue
        match = MatchNode(target, child.attrib)
        if not match.load_from_elem(child):
          return False
        self._subnodes.append(match)
      elif child.tag == 'struct':
        struct = StructNode(target, child.attrib)
        if not struct.load_from_elem(child, targets):
          logging.error('struct call struct load_from_elem error')
          return False
        self._subnodes.append(struct)
      else:
        logging.error('unknown child in struct: %s' % child.tag)
        return False
    return True

  def process(self, tree):
    for path in self._xpath:
      result = []
      trees = tree.xpath(path)
      if not trees:
        continue
      for tree in trees:
        sub_result = {}
        for node in self._subnodes:
          data = node.process(tree)
          if not data:
            continue
          for key, value in data.items():
            if key not in sub_result:
              sub_result[key] = value
        if sub_result:
          result.append(sub_result)

      return {self._target: result}

  def show_info(self):
    logging.debug('struct')
    for xpath in self._xpath:
      logging.debug('xpath: %s'%xpath)
    for node in self._subnodes:
      node.show_info()

node_map = {'match': MatchNode,
            'struct': StructNode}

class TemplateParser(object):
  def __init__(self, template_path):
    self._nodes = []
    self._url_pattern = ''
    self._encoding = None
    self._template_path = template_path

  def init_template(self, targets):
    #logging.debug("initing file: %s" % self._template_path)
    tree = etree.parse(self._template_path)
    url_pattern_elem = tree.find('url_pattern')
    if url_pattern_elem is None:
      raise Exception("url_pattern is missed, template_path: %s" % self._template_path)
    self._url_pattern = url_pattern_elem.text

    encoding_elem = tree.find('encoding')
    if encoding_elem is not None:
      self._encoding = encoding_elem.text
    else:
      self._encoding = 'utf8'

    children = tree.getroot().getchildren()
    for elem in children:
      if elem.tag not in node_map:
        continue
      target = elem.get('target')
      if not target:
        logging.error('target is missed')
        return False
      if targets and elem.tag == 'match' and target not in targets:
        continue

      node = node_map[elem.tag](target, elem.attrib)
      if node.load_from_elem(elem, targets):
        self._nodes.append(node)
      else:
        return False
    return True

  def parse(self, url, html, is_xml=False):
    pattern = re.compile(self._url_pattern)
    if not pattern.match(url):
      return None
    logging.debug("template %s matched for url %s" % (
      os.path.basename(self._template_path), url))
    if self._encoding and not is_xml:
      html = html.decode(self._encoding, 'ignore')
    try:
      html_tree = etree.XML(html) if is_xml else etree.HTML(html)
    except:
      logging.exception('failed to parse html for url: %s', url)
      return None
    result = {}
    try:
      lost_nodes = []
      for node in self._nodes:
        data = node.process(html_tree)
        if not data:
          if node._target not in lost_nodes:
            lost_nodes.append(node._target)
          #temp_logger.error('template wrong,url:%s,target:%s,template:%s' % (url, node._target, self._template_path))
          continue
        for key, value in data.items():
          if key not in result:
            result[key] = value
      for key in lost_nodes:
        if key not in result:
          temp_logger.error('template wrong,url:%s,target:%s,template:%s' % (url, key, self._template_path))
      if not result:
        logging.warning('templates %s parse result length 0' % os.path.basename(self._template_path))
        return None
    except:
      logging.exception('failed parse, template: %s', self._template_path)
      raise
    return result


  def show_info(self):
    for node in self._nodes:
      node.show_info()

class Xpather:
  def __init__(self, targets=None):
    self._template_parser_list = []
    self._targets = targets

  def load_templates(self, dir_path):
    files = os.listdir(dir_path)
    for f in files:
      if not f.endswith('xml'):
        continue
      template_path = os.path.join(dir_path, f)
      template_parser = TemplateParser(template_path)
      try:
        template_parser.init_template(self._targets)
      except:
        logging.exception('failed to init template, %s', template_path)
        raise
      #template_parser.show_info()
      self._template_parser_list.append(template_parser)

  def parse(self, url, html, is_xml=False):
    if not html or not url:
      return None
    result_data = {}
    for parser in self._template_parser_list:
      data = parser.parse(url, html, is_xml)
      if data and (len(data) > len(result_data)):
        result_data = data
    return result_data

  def parse_from_url(self, url):
    html = urlopen(url).read()
    return self.parse(url, html)
