#!/usr/bin/python
# -*- coding: utf-8 -*-
# 初始jar包及配置文件文件夹,jar文件及配置文件以实例名为文件名,文件名中不包含版本号
APP_JARS = 'C://data/jars/'
# 运行目录,不要手动创建,启动时判断目录是否存在来初始化项目
APP_ROOT = 'C://data/nutzwk/'
# jar文件名,名称要保持与配置文件里 nutz.application.name 值一致
APP_LIST = [
    'wk-nb-service-sys',
    'wk-nb-web-api',
    'wk-nb-service-cms',
	'wk-nb-web-vue'
]
# jar包启动的jvm配置参数
APP_OPTS = {
    'wk-nb-service-cms': ''
}
# 通信密钥,保持与 wk-nb-web-api 模块里配置内容一致,用于心跳通信
HTTP_SECRET_ID = 'wizzer'
HTTP_SECRET_KEY = 'nutzwk'
# API路径
HTTP_URL = 'http://127.0.0.1:9001/open/api/deploy'
# 心跳周期(单位:秒)
HTTP_HEARTBEAT = 10
HTTP_TIMEOUT = 5

CACHE_TASK_IDS = []
CACHE_HOST_NAME = ''
