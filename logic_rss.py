# -*- coding: utf-8 -*-
#########################################################
# python
import os
import traceback
import time
import threading
import json
import datetime
import re

# third-party
from sqlalchemy import desc
from sqlalchemy import or_, and_, func, not_

# sjva 공용
from framework import db, scheduler, path_app_root, SystemModelSetting
from framework.job import Job
from framework.util import Util
from framework.common.rss import RssUtil
import framework.common.celery as celery_task

# 패키지
from .plugin import logger, package_name
from .model import ModelSetting, ModelOffcloud2Account, ModelOffcloud2Job,  ModelOffcloud2Item, ModelOffcloud2Cache
from .offcloud_api import Offcloud

#########################################################


class LogicRss(object): 


    @staticmethod
    def process_insert_feed():
        try:
            job_list = ModelOffcloud2Job.get_list()
            for job in job_list:
                try:
                    logger.debug('Offcloud job:%s', job.id)
                    feed_list = RssUtil.get_rss(job.rss_url)
                    if not feed_list:
                        continue
                    flag_commit = False
                    count = 0
                    #
                    for feed in reversed(feed_list):
                        if db.session.query(ModelOffcloud2Item).filter_by(job_id=job.id, link=feed.link).first() is None:
                            r = ModelOffcloud2Item()
                            r.title = feed.title
                            r.link = feed.link
                            #db.session.add(r)
                            job.rss_list.append(r)
                            flag_commit = True
                            count += 1
                    if flag_commit:
                        db.session.commit()
                    logger.debug('Offcloud job:%s flag_commit:%s count:%s', job.id, flag_commit, count)
                except Exception as e:
                    logger.error(e)
                    logger.error(traceback.format_exc())
        except Exception as e:
            logger.error(e)
            logger.error(traceback.format_exc())
    
    @staticmethod
    def process_cached_list(rss_list):
        magnet_list = []
        for r in rss_list:
            if r.link.startswith('magnet'):# and r.oc_cached is not True:
                try:
                    magnet_list.append(r.link[20:60])
                except:
                    logger.error(e)
                    logger.error(traceback.format_exc())
        cached_list = Offcloud.get_cache_list(ModelSetting.get('apikey'), magnet_list)     
        return cached_list


    # Cache 확인되고 다운로드 요청한 피드 처리
    @staticmethod
    def process_cached_feed(feed):
        try:
            # 이미 봇으로 받았던거면 패스
            entity = ModelOffcloud2Cache.get_by_magnet(feed.link)
            if entity is not None:
                return
            if feed.link_to_notify_status is not None and feed.link_to_notify_status == '1':
                return
            # sjva server에게만 알리는 것으로 변경. 서버가 대신 뿌림
            telegram = {
                'title' : feed.title,
                'magnet' : feed.link,
                'who' : SystemModelSetting.get('id')
            }
            telegram_text = json.dumps(telegram, indent=2)
            try:
                import requests
                sjva_server_url = 'https://sjva-server.soju6jan.com/ss/api/off_cache2'
                data = {'data':telegram_text}
                res = requests.post(sjva_server_url, data=data)
                tmp = res.content
                feed.link_to_notify_status = '1'
                db.session.add(feed)
                db.session.commit()
                if res.content == 'append':
                    return True
                elif res.content == 'exist':
                    return False
            except Exception as e:
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())    
            return True
        except Exception as e:
            logger.error(e)
            logger.error(traceback.format_exc())


    @staticmethod
    def scheduler_function():
        LogicRss.scheduler_function_rss_request()
        LogicRss.scheduler_function_tracer()

    # status
    # 0 : 초기 값
    # 1 : 마그넷. 캐쉬. 오버
    # 2 : 마그넷. 노캐쉬. 오버
    # 3 : 일반파일. 오버
    # 4 : 수동요청. 오버
    # 6 : 마그넷. 캐쉬. 요청 성공
    # 7 : 마그넷. 노캐쉬. 요청 성공
    # 8 : 일반파일. 요청 성공 
    # 9 : 수동요청 성공
    # 11 : 완료
    # 12 : job 모드 캐시확인만. 마그넷. 캐시확인 완료.
    # 13 : error
    # 14 : NOSTATUS


    @staticmethod
    def scheduler_function_rss_request():
        logger.debug('1. RSS to DB')
        LogicRss.process_insert_feed()

        try:
            over_flag = False
            apikey = ModelSetting.get('apikey')
            job_list = ModelOffcloud2Job.get_list()
            for job in job_list:
                account = ModelOffcloud2Account.get(job.username)
                
                rss_list = ModelOffcloud2Item.get_rss_list_by_scheduler(job)

                cached_list = LogicRss.process_cached_list(rss_list)
                logger.debug('2. job name:%s count:%s, cache count:%s', job.name, len(rss_list), len(cached_list))

                for feed in rss_list:
                    try:
                        # 요청 안한 것들
                        if feed.status < 6:
                            feed.oc_folderid = job.folderid
                            if feed.link.startswith('magnet'):
                                if feed.link[20:60] in cached_list:
                                    LogicRss.process_cached_feed(feed)
                                    feed.oc_cached = True
                                    
                                    if job.mode == '0' or job.mode == '1': 
                                        if over_flag:
                                            feed.status = 1
                                        else:
                                            feed.remote_time = datetime.datetime.now()
                                            ret = Offcloud.add_remote(apikey, feed, account.option_id)
                                            if feed.job.use_tracer:
                                                feed.make_torrent_info()
                                            #logger.debubg("요청 : %s", feed.title)
                                            if ret == 'over':
                                                over_flag = True
                                                feed.status = 1
                                            else:
                                                feed.status = 6
                                    elif job.mode == '2': #Cache 확인만
                                        feed.status = 12
                                else:
                                    # Cache 안되어 있을때
                                    if job.mode == '1': # Cache 안되어 있어도 받는 모드
                                        if over_flag:
                                            feed.status = 2
                                        else:
                                            feed.remote_time = datetime.datetime.now()
                                            ret = Offcloud.add_remote(apikey, feed, account.option_id)
                                            if feed.job.use_tracer:
                                                feed.make_torrent_info()
                                            if ret == 'over':
                                                over_flag = True
                                                feed.status = 2
                                            else:
                                                feed.status = 7

                            elif feed.link.startswith('http'):
                                if ModelSetting.get_bool('request_http_start_link'):
                                    if not feed.link.endswith('=.torrent'):
                                        feed.remote_time = datetime.datetime.now()
                                        ret = Offcloud.add_remote(apikey, feed, account.option_id)
                                        if ret == 'over':
                                            over_flag = True
                                            feed.status = 3
                                        else:
                                            feed.status = 8
                        else:
                            if feed.oc_status == 'created' or feed.oc_status == 'uploading' or feed.oc_status == 'downloading':
                                Offcloud.refresh_status(apikey, feed)

                            if feed.oc_status == 'downloaded':
                                feed.status = 11
                                feed.completed_time = datetime.datetime.now()
                            if feed.oc_status == 'error':
                                feed.status = 13
                            if feed.oc_status == 'NOSTATUS':
                                feed.status = 14

                    except Exception as e:
                        logger.error(e)
                        logger.error(traceback.format_exc())
                    finally:
                        db.session.add(feed)
            db.session.commit()
        except Exception as e:
            logger.error(e)
            logger.error(traceback.format_exc())
        finally:
            logger.debug('==================================')


    @staticmethod
    def add_remote(req):
        try:
            rss_id = req.form['id']
            apikey = db.session.query(ModelSetting).filter_by(key='apikey').first().value
            feed = db.session.query(ModelOffcloud2Item).filter_by(id=rss_id).with_for_update().first()
            account = ModelOffcloud2Account.get(feed.job.username)
            
            feed.remote_time = datetime.datetime.now()
            ret = Offcloud.add_remote(apikey, feed, account.option_id)
            if feed.job.use_tracer:
                feed.make_torrent_info()
            if ret == 'over':
                feed.status = 4
            else:
                feed.status = 9
            db.session.commit()
            return True
        except Exception, e:
            logger.debug('Exception:%s', e)
            logger.debug(traceback.format_exc())
            return False


    @staticmethod
    def scheduler_function_tracer():
        try:
            job_list = ModelOffcloud2Job.get_list()
            for job in job_list:
                if not job.use_tracer:
                    continue

                # 토렌트 인포가 실패할수도 있고, 중간에 추가된 경우도 있기 때문에... 기존에 없었던 경우도 있기때문에..
                query = db.session.query(ModelOffcloud2Item) \
                    .filter(ModelOffcloud2Item.job_id == job.id ) \
                    .filter(ModelOffcloud2Item.oc_status != None ) \
                    .filter(ModelOffcloud2Item.created_time > datetime.datetime.now() + datetime.timedelta(days=ModelSetting.get_int('tracer_max_day')*-1)) \
                    .filter(ModelOffcloud2Item.torrent_info == None)
                items = query.all()
                logger.debug(len(items))
                if items:
                    for feed in items:
                        feed.make_torrent_info()
                        db.session.add(feed)
                        logger.debug(feed.title)
                        db.session.commit()
                

                lists = os.listdir(job.mount_path)
                for target in lists:
                    try:
                        logger.debug(target)
                        fullpath = os.path.join(job.mount_path, target)

                        # 자막파일은 바로 이동
                        if os.path.splitext(target.lower())[1] in ['.smi', '.srt', 'ass']:
                            celery_task.move(fullpath, job.move_path)
                            continue

                        # 해쉬 변경
                        match = re.match(r'\w{40}', target)
                        if match:
                            feeds = db.session.query(ModelOffcloud2Item).filter(ModelOffcloud2Item.link.like('%' + target)).all()
                            if len(feeds) == 1:
                                logger.debug(feeds[0].dirname)
                                logger.debug(len(feeds[0].dirname))
                                logger.debug(feeds[0].filename)

                                if feeds[0].dirname != '':
                                    new_fullpath = os.path.join(job.mount_path, feeds[0].dirname)
                                else:
                                    new_fullpath = os.path.join(job.mount_path, feeds[0].filename)
                                if not os.path.exists(new_fullpath):
                                    celery_task.move(fullpath, new_fullpath)
                                    logger.debug('Hash %s %s', fullpath, new_fullpath)
                                    fullpath = new_fullpath
                                    target = os.path.basename(new_fullpath)
                                else:
                                    logger.debug('HASH NOT MOVED!!!!!!!')

                        if os.path.isdir(fullpath):
                            feeds = db.session.query(ModelOffcloud2Item).filter(ModelOffcloud2Item.dirname == target).all()
                        else:
                            feeds = db.session.query(ModelOffcloud2Item).filter(ModelOffcloud2Item.filename == target).all()
                        logger.debug('Feeds count : %s', len(feeds))
                        
                        # 이규연의 스포트라이트 _신천지 위장단체와 정치_.E237.200319.720p-NEXT
                        # 이규연의 스포트라이트 (신천지 위장단체와 정치).E237.200319.720p-NEXT.mp4
                        # 특수문자를 _으로 변경하는 경우 있음. 일단.. 파일만
                        if len(feeds) == 0:
                            if os.path.isdir(fullpath):
                                pass
                            else:
                                query = db.session.query(ModelOffcloud2Item)
                                for t in target.split('_'):
                                    query = query.filter(ModelOffcloud2Item.filename.like('%'+t+'%' ))
                                feeds = query.all()
                                if len(feeds) == 1:
                                    #rename
                                    new_fullpath = os.path.join(job.mount_path, feeds[0].filename)
                                    celery_task.move(fullpath, new_fullpath)
                                    fullpath = new_fullpath
                                else:
                                    logger.debug('EEEEEEEEEEEEEEEEEEEEEEE')

                        for feed in feeds:
                            logger.debug('제목 : %s, %s', feed.title, feed.filecount)
                            flag = True
                            for tmp in feed.torrent_info['files']:
                                logger.debug('tmp : %s', tmp['path'])
                                logger.debug(os.path.split(tmp['path']))
                                if os.path.split(tmp['path'])[0] != '':
                                    tmp2 = os.path.join(job.mount_path, os.path.sep.join(os.path.split(tmp['path'])))
                                else:
                                    tmp2 = os.path.join(job.mount_path, tmp['path'])
                                logger.debug('Feed check : %s', tmp2)
                                if os.path.exists(tmp2):
                                    logger.debug('File Exist : True')
                                else:
                                    logger.debug('File Exist : False')
                                    flag = False
                                    break
                            if flag:
                                dest_fullpath = os.path.join(job.move_path, target)
                                if os.path.exists(dest_fullpath):
                                    dup_folder = os.path.join(job.mount_path, u'중복')
                                    if not os.path.exists(dup_folder):
                                        os.makedirs(dup_folder)
                                    dest_folder = dup_folder
                                else:
                                    dest_folder = job.move_path
                                celery_task.move(fullpath, dest_folder)
                                logger.debug('MOVE : %s' % fullpath)
                    except Exception, e:
                        logger.debug('Exception:%s', e)
                        logger.debug(traceback.format_exc())


        except Exception, e:
            logger.debug('Exception:%s', e)
            logger.debug(traceback.format_exc())
            return False

    @staticmethod
    def check_folder_and_info(folder, feed):
        try:
            logger.debug(feed.torrent_info['files'])
            for tmp in feed.torrent_info['files']:
                logger.debug('tmp : %s', tmp['path'])




        except Exception, e:
            logger.debug('Exception:%s', e)
            logger.debug(traceback.format_exc())