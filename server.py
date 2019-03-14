#!/usr/bin/python
# -*- coding: utf-8 -*-
import json
import logging.handlers
import os
import platform
import random
import sched
import shutil
import signal
import socket
import subprocess
import threading
import time
from urllib import request, parse

import osutil
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

hostname = socket.gethostname()
settings.CACHE_HOST_NAME = hostname

# 初始化sched模块的scheduler类
# 第一个参数是一个可以返回时间戳的函数，第二个参数可以在定时未到达之前阻塞。  
schedule = sched.scheduler(time.time, time.sleep)


# 被周期性调度触发的函数
def heart():
    http()
    schedule.enter(settings.HTTP_HEARTBEAT, 0, heart)


def init():
    # 延迟几秒,让项目启动完全
    time.sleep(10)
    # enter四个参数分别为: 间隔时间、优先级、被调用触发的函数、传递参数,如果只有一个参数需加,号 (xxx,)
    schedule.enter(settings.HTTP_HEARTBEAT, 0, heart)
    schedule.run()


# 心跳请求,定时获取最新任务
def http():
    url = settings.HTTP_URL + "/task"
    now = int(time.time())
    nonce = ''.join(random.sample('abcdefghijklmnopqrstuvwxyz0123456789', 32))
    headers = {
        r'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.109 Safari/537.36',
        r'Accept': 'application/json, text/javascript, */*; q=0.01',
        r'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
    }
    data = {
        'appid': settings.HTTP_SECRET_ID,
        'nonce': nonce,
        'timestamp': str(now),
        'hosts': ','.join(settings.APP_LIST),
        'hostname': settings.CACHE_HOST_NAME
    }
    sign = osutil.createSign(settings.HTTP_SECRET_KEY, data)
    data['sign'] = sign
    data = parse.urlencode(data).encode('utf-8')
    try:
        req = request.Request(url, data, headers, None, None, 'POST')
        page = request.urlopen(req, None, settings.HTTP_TIMEOUT).read()
        result = page.decode('utf-8')
        log.debug(result)
        res_data = json.loads(result)
        if res_data['code'] == 0:
            task_list = res_data['data']
            for task in task_list:
                # 将任务ID放到缓存里,防止重复执行同一个任务
                if task['id'] in settings.CACHE_TASK_IDS:
                    log.debug('任务已存在,任务ID:::' + task['id'])
                else:
                    settings.CACHE_TASK_IDS.append(task['id'])
                    t = execTaskThread(task['id'], task)
                    t.start()
                    log.debug('任务已添加,任务ID:::' + task['id'])
    except Exception as e:
        log.error(str(e) + ':::' + url)


# 杀死进程
def killProcess(pid):
    sysname = platform.system()
    try:
        if sysname == 'Linux':
            os.kill(int(pid), signal.SIGKILL)
            result = {'code': 0, 'msg': '已杀死PID为 %s 的进程' % (pid)}
        elif sysname == 'Windows':
            os.kill(int(pid), -1)
            result = {'code': 0, 'msg': '已杀死PID为 %s 的进程' % (pid)}
        else:
            result = {'code': -1, 'msg': '不支持的操作系统::' + platform.system()}
    except OSError as e:
        log.error('杀死进程出错::' + str(e))
        result = {'code': -2, 'msg': '杀死进程出错::' + str(e)}
    return result


# 启动jar程序
class startJavaThread(threading.Thread):

    def __init__(self, appname):
        threading.Thread.__init__(self)
        self.appname = appname
        self.daemon = True

    def run(self):
        _env = os.environ.copy()
        _env["APPNAME"] = self.appname
        appversion = osutil.getAppVersion(self.appname)
        confversion = osutil.getConfVersion(self.appname)
        apppath = settings.APP_ROOT + self.appname + '/app/' + appversion + '/' + self.appname + '.jar'
        confpath = settings.APP_ROOT + self.appname + '/conf/' + confversion + '/'
        try:
            jvm = settings.APP_OPTS[self.appname]
        except KeyError as e:
            jvm = ''
        cmd = 'java ' + ' -Dnutz.boot.configure.properties.dir=' + confpath + ' ' + jvm + ' -jar ' + apppath
        log.info(cmd)
        with open("/data/python/" + self.appname + ".log", "w") as f:
            subprocess.call(cmd, close_fds=True, shell=True, env=_env, stdout=f, stderr=f)


# 执行任务命令
class execTaskThread(threading.Thread):

    def __init__(self, taskid, task):
        threading.Thread.__init__(self)
        self.taskid = taskid
        self.task = task
        self.daemon = False

    def run(self):
        action = self.task['action']
        if 'stop' == action:
            result = killProcess(self.task['processId'])
            if result['code'] == 0:
                settings.CACHE_TASK_IDS.remove(self.taskid)
                report(self.taskid, 2, '执行成功')
            else:
                report(self.taskid, 3, result['msg'])
        if 'start' == action:
            appname = self.task['name']
            appversion = self.task['appVersion']
            confversion = self.task['confVersion']
            ok = True
            # 判断程序版本是否存在,不存在则下载,并把version文件移到新文件夹
            if not os.path.exists(settings.APP_ROOT + appname + '/app/' + appversion + '/' + appname + '.jar'):
                try:
                    os.makedirs(settings.APP_ROOT + appname + '/app/' + appversion)
                except Exception as e:
                    log.error(str(e))
                if dowload('jar', appname, appversion) == True:
                    oldappversion = osutil.getAppVersion(appname)
                    if oldappversion != appversion:
                        shutil.move(settings.APP_ROOT + appname + '/app/' + oldappversion + '/version',
                                    settings.APP_ROOT + appname + '/app/' + appversion + '/version')
                else:
                    ok = False
                    report(self.taskid, 3, 'Jar包下载失败')
            # 判断配置文件是否存在,存在则下载并覆盖,不存在则下载
            if not os.path.exists(settings.APP_ROOT + appname + '/conf/' + confversion + '/' + appname + '.properties'):
                try:
                    os.makedirs(settings.APP_ROOT + appname + '/conf/' + confversion)
                except Exception as e:
                    log.error(str(e))
            if dowload('conf', appname, appversion) == True:
                oldconfversion = osutil.getConfVersion(appname)
                if oldconfversion != confversion:
                    shutil.move(settings.APP_ROOT + appname + '/conf/' + oldconfversion + '/version',
                                settings.APP_ROOT + appname + '/conf/' + confversion + '/version')
            else:
                ok = False
                report(self.taskid, 3, '配置文件下载失败')
            if ok:
                t = startJavaThread(appname)
                t.start()


def dowload(type, appname, appversion):
    if type == 'conf':
        url = settings.HTTP_URL + "/conf/download"
    else:
        url = settings.HTTP_URL + "/jar/download"
    now = int(time.time())
    nonce = ''.join(random.sample('abcdefghijklmnopqrstuvwxyz0123456789', 32))
    headers = {
        r'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.109 Safari/537.36',
        r'Accept': 'application/json, text/javascript, */*; q=0.01',
        r'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
    }
    data = {
        'appid': settings.HTTP_SECRET_ID,
        'nonce': nonce,
        'timestamp': str(now),
        'hosts': ','.join(settings.APP_LIST),
        'hostname': settings.CACHE_HOST_NAME,
        'appname': appname,
        'appversion': appversion
    }
    sign = osutil.createSign(settings.HTTP_SECRET_KEY, data)
    data['sign'] = sign
    data = parse.urlencode(data).encode('utf-8')
    try:
        req = request.Request(url, data, headers, None, None, 'POST')
        data = request.urlopen(req, None, settings.HTTP_TIMEOUT).read()
        if type == 'conf':
            filepath = settings.APP_ROOT + appname + '/conf/' + appversion + "/" + appname + '.properties'
        else:
            filepath = settings.APP_ROOT + appname + '/app/' + appversion + "/" + appname + '.jar'
        with open(filepath, "wb+") as file:
            file.write(data)
            file.close()
        return True
    except Exception as e:
        log.error(str(e) + ':::' + url)
        return False


# status 0-待执行,1-执行中,2-执行成功,3-执行失败,4-撤销任务
def report(taskid, status, msg):
    url = settings.HTTP_URL + "/report"
    now = int(time.time())
    nonce = ''.join(random.sample('abcdefghijklmnopqrstuvwxyz0123456789', 32))
    headers = {
        r'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.109 Safari/537.36',
        r'Accept': 'application/json, text/javascript, */*; q=0.01',
        r'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
    }
    data = {
        'appid': settings.HTTP_SECRET_ID,
        'nonce': nonce,
        'timestamp': str(now),
        'hosts': ','.join(settings.APP_LIST),
        'hostname': settings.CACHE_HOST_NAME,
        'taskid': taskid,
        'status': str(status),
        'msg': msg
    }
    sign = osutil.createSign(settings.HTTP_SECRET_KEY, data)
    data['sign'] = sign
    data = parse.urlencode(data).encode('utf-8')
    try:
        req = request.Request(url, data, headers, None, None, 'POST')
        request.urlopen(req, None, settings.HTTP_TIMEOUT).read()
    except Exception as e:
        log.error(str(e) + ':::' + url)