#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging.handlers
import math
import os
import shutil
import time

import server
import settings

if not os.path.exists('/data/python'):
    os.makedirs('/data/python')
log = logging.getLogger()
log.setLevel(logging.DEBUG)
fh = logging.handlers.RotatingFileHandler("/data/python/watchdog.log", maxBytes=16 * 1024 * 1024,
                                          backupCount=1, encoding="UTF-8")
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('$: %(asctime)s > %(levelname)-5s > %(filename)s:%(lineno)s > %(message)s')
fh.setFormatter(formatter)
log.addHandler(fh)

# 初始化运行目录
if not os.path.exists(settings.APP_ROOT):
    now = time.time()
    log.info('初始化运行目录: ' + settings.APP_ROOT)
    os.makedirs(settings.APP_ROOT)
    for appName in settings.APP_LIST:
        if not os.path.exists(settings.APP_ROOT + appName):
            try:
                os.makedirs(settings.APP_ROOT + appName + '/app/0/')
                os.makedirs(settings.APP_ROOT + appName + '/conf/0/')
                shutil.copyfile(settings.APP_JARS + appName + '.jar',
                                settings.APP_ROOT + appName + '/app/0/' + appName + '.jar')
                shutil.copyfile(settings.APP_JARS + appName + '.properties',
                                settings.APP_ROOT + appName + '/conf/0/' + appName + '.properties')
                file = open(settings.APP_ROOT + appName + '/app/0/version', 'w')
                file.write("")
                file.close()
                file = open(settings.APP_ROOT + appName + '/conf/0/version', 'w')
                file.write("")
                file.close()
            except Exception as e:
                log.error('运行目录初始化出错::' + str(e))
    log.info('初始化运行目录完成,耗时: ' + str(math.ceil(1000 * (time.time() - now))) + "ms")
else:
    log.info('运行目录已存在,开始启动项目...')

for appName in settings.APP_LIST:
    try:
        t = server.startJavaThread(appName)
        t.start()
    except Exception as e:
        log.error(str(e))

# 启动守护进程
if __name__ == '__main__':
    server.init()
