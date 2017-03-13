#! /usr/bin/env python
# -*- coding: utf-8 -*-

import configparser
import os
import smtplib
import sys
import time
from email.header import Header
from email.mime.text import MIMEText
from email.utils import parseaddr, formataddr

import requests

debug = True


def log(msg):
    if debug:
        print(msg)


def monitor():
    # 加载配置文件信息
    log('\n>>>>>>>>>> 脚本开始运行 <<<<<<<<<<\n')
    config = configparser.ConfigParser()
    dirname, filename = os.path.split(os.path.abspath(sys.argv[0]))  # 获取绝对目录
    config.read(dirname + '/ds.config')  # 当前目录下的ds.config

    # 初始化配置信息
    duoshuo_account = {}
    email_info = {}
    period_time = {}
    items2dict(duoshuo_account, config.items('duoshuo_account'))
    items2dict(email_info, config.items('email_info'))
    items2dict(period_time, config.items('period_time'))

    name = duoshuo_account.get('name')
    account_id = duoshuo_account.get('id')
    period = int(period_time.get('period'))
    secret = duoshuo_account.get('secret')

    # 多说后台获取 log 数据的接口
    duoshuo_log_url = 'http://api.duoshuo.com/log/list.json?' \
                      + 'short_name=' + name \
                      + '&secret=' + secret \
                      + '&limit=5000'

    # 第一次获取账户后台的初始信息
    current_count, meta = get_duoshuo_log(duoshuo_log_url)
    last_count = current_count
    log('账号初始加载数据条数：' + str(last_count))

    while True:  # 轮询检查
        log('\n----->> get_duoshuo_log')
        current_count, meta = get_duoshuo_log(duoshuo_log_url)
        # send_email(email_info, name, current_count, (current_count - last_count), meta)
        log('当前数据条数：' + str(current_count))
        # print u'meta --->  ' + str(meta)
        if (len(meta)) > 0 and (current_count > last_count) and (account_id != meta.get('author_id')):
            send_email(email_info, name, current_count, (current_count - last_count), meta)
            last_count = current_count
        time.sleep(period)


# 把option的items映射到dict中
def items2dict(options_dict, items_list):
    for item in items_list:
        options_dict[item[0]] = item[1]


# 获取多说账户的后台信息log
def get_duoshuo_log(url):
    # print url
    count = 0
    meta = {}
    try:
        r = requests.get(url, timeout=15)
        resp = r.json()
        count = len(resp['response'])
        action = resp['response'][count - 1]['action']  # 目前只是抓取最后一条
        if (resp['code'] == 0) and (action == 'create'):
            meta = resp['response'][count - 1]['meta']
    except Exception as e:
        log('!!!Error' + str(e))  # TimeOut
    finally:
        return count, meta


# 发送邮件
def send_email(email_info, name, current_count, count, meta):
    log('----->> send email')
    last_meta_message = '最新评论信息：' \
                        + '\n用户地址：' + str(meta.get('ip')) \
                        + '\n用户昵称：' + str(meta.get('author_name')) \
                        + '\n用户邮箱：' + str(meta.get('author_email')) \
                        + '\n用户网站：' + str(meta.get('author_url')) \
                        + '\n评论文章：' + str(meta.get('thread_key')) \
                        + '\n评论时间：' + str(meta.get('created_at')) \
                        + '\n评论内容：' + str(meta.get('message')) \
                        + '\n审核状态：' + str(meta.get('status'))

    duoshuo_admin_url = 'http://' + name + '.duoshuo.com/admin/'
    text = '后台记录变更数：' + str(count) + '\n多说后台：' + duoshuo_admin_url + '\n\n' + last_meta_message;
    log(text)

    def _format_addr(s):
        name, addr = parseaddr(s)
        return formataddr((Header(name, 'utf-8').encode(), addr))

    msg = MIMEText(text, 'plain', 'utf-8')
    msg['From'] = _format_addr('多说扫描姬 <%s>' % email_info.get('from_address'))
    msg['To'] = _format_addr('喵呜~ <%s>' % email_info.get('to_address'))
    msg['Subject'] = Header('多说评论通知 #' + str(current_count), 'utf-8').encode()

    log('发送的信息：\n' + str(msg))

    try:
        server = smtplib.SMTP(email_info.get('email_host'))  # 我的是 smtp.qq.com:587
        server.starttls()
        server.login(email_info.get('from_address'), email_info.get('password'))
        server.sendmail(email_info.get('from_address'), [email_info.get('to_address')], msg.as_string())
        log('发送邮件完成')
    except Exception as e:
        log('邮件发送失败：' + str(e))
    finally:
        server.quit()


if __name__ == '__main__':
    monitor()
