#!/usr/bin/python
# -*- coding: utf-8 -*-
import hashlib
import os
import psutil

import settings


def netstat():
    status_temp = []
    net_connections = psutil.net_connections()
    for key in net_connections:
        status_temp.append(key.status)
    return status_temp.count("ESTABLISHED")


# 签名算法

def createSign(appkey, params):
    sign = ''
    list = sorted(params.items(), key=lambda params: params[0], reverse=False)
    for k, v in list:
        sign = sign + k + '=' + v + '&'
    sign = sign + 'appkey=' + appkey
    m2 = hashlib.md5()
    m2.update(sign.encode('utf-8'))
    return m2.hexdigest()


# 获取当前程序版本
def getAppVersion(appname):
    path = settings.APP_ROOT + appname + '/app/'
    if os.path.exists(path):
        dirs = os.listdir(path)
        for dir in dirs:
            if os.path.exists(path + dir + '/version'):
                return str(dir)
    return ''


# 获取当前配置文件版本
def getConfVersion(appname):
    path = settings.APP_ROOT + appname + '/conf/'
    if os.path.exists(path):
        dirs = os.listdir(path)
        for dir in dirs:
            if os.path.exists(path + dir + '/version'):
                return str(dir)
    return ''
