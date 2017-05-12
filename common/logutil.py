#!/usr/bin/python
#

__author__ = 'clhou@oklantu.com'

import logging
from logging.handlers import RotatingFileHandler

class Log(object):
  def __init__(self, log_id, log_path, log_level=logging.INFO):
    self.logger_ = logging.getLogger(log_id)
    self._handler = RotatingFileHandler(log_path, mode='a', maxBytes=100 * 1024 * 1024, backupCount=2)
    self._handler.setFormatter(logging.Formatter("%(asctime)s-%(filename)s:%(lineno)d[%(levelname)s]:%(message)s"))
    self.logger_.setLevel(log_level)
    self._handler.setLevel(log_level)
    self.logger_.addHandler(self._handler)

  def __del__(self):
    self._handler.close()

  def setdebuglevel(self):
    self.logger_.setLevel(logging.DEBUG)

  def setinfolevel(self):
    self.logger_.setLevel(logging.INFO)

  @property
  def log(self):
    return self.logger_

