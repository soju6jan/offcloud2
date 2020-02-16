# -*- coding: utf-8 -*-
#########################################################
# python
import os
import traceback
import time
import threading
import json
import datetime

# third-party
from sqlalchemy import desc
from sqlalchemy import or_, and_, func, not_

# sjva 공용
from framework import db, scheduler, path_app_root, SystemModelSetting
from framework.job import Job
from framework.util import Util
from framework.common.rss import RssUtil

# 패키지
from .plugin import logger, package_name
from .model import ModelSetting, ModelOffcloud2Account, ModelOffcloud2Job,  ModelOffcloud2Item, ModelOffcloud2Cache
from .offcloud_api import Offcloud
#########################################################


class LogicCache(object): 

    @staticmethod
    def process_telegram_data(data):
        try:
            logger.debug('receive data')
            logger.debug(data)
            type_list = ModelSetting.get('cache_save_type_list').split('|')
            type_list = Util.get_list_except_empty(type_list)
            if len(type_list) == 0 or data['t'] in type_list:
                ret = ModelOffcloud2Cache.add(data)
                if ret is not None:
                    logger.debug('Offcloud2 %s append' % ret.name)
                    if ModelSetting.get_bool('cache_receive_info_send_telegram'):
                        import telegram_bot
                        msg = '😉 Offcloud2 캐쉬 정보 수신\n'
                        msg += 'Type : %s\n' % data['t']
                        msg += '%s\n' % data['n']
                        from system.model import ModelSetting as SystemModelSetting
                        ddns = SystemModelSetting.get('ddns')
                        msg += '➕ 리모트 다운로드 추가\n%s/%s/api/cache_download?id=%s' % (ddns, package_name, ret.id)
                        telegram_bot.TelegramHandle.sendMessage(msg)

        except Exception as e:
            logger.error(e)
            logger.error(traceback.format_exc())
    
    
    @staticmethod
    def cache_download(req):
        try:
            apikey = ModelSetting.get('apikey')
            h = db.session.query(ModelOffcloud2Cache).filter_by(id=req.args.get('id')).first().magnet

            if len(h) == 40:
                h = 'magnet:?xt=urn:btih:' + h
            
            username = ModelSetting.get('default_username')
            entity = ModelOffcloud2Account.get(username)
            if entity is not None:
                remoteOptionId = entity.option_id
            else:
                return 'not exist username'
            folder_id = ModelSetting.get('default_folder_id')
            ret = Offcloud.add_remote_by_magnet(apikey, h, remoteOptionId, folder_id)
            return ret
        except Exception, e:
            logger.debug('Exception:%s', e)
            logger.debug(traceback.format_exc())
            return str(e)



