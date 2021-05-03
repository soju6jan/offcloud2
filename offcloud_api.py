# -*- coding: utf-8 -*-
#########################################################
# python
import traceback
import json
import logging

# third-party
import requests
# sjva 공용
from framework import py_urllib, py_urllib2
# 패키지
from .plugin import logger, package_name
#########################################################

class Offcloud(object):

    @staticmethod
    def get_cache_list(key, magnet_list):
        try:
            url = 'https://offcloud.com/api/torrent/check?key=%s' % (key)
            params = {'hashes' : magnet_list}
            res = requests.post(url, json=params)
            result = res.json()
            return result['cachedItems']
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return None 


    @staticmethod
    def get_remote_account(key):
        try:
            url = 'https://offcloud.com/api/remote/accounts'
            params = {'key' : key}
            postdata = py_urllib.urlencode(params).encode('utf-8')  
            request = py_urllib2.Request(url, postdata)
            response = py_urllib2.urlopen(request)
            data = json.load(response)
            if 'data' in data:
                return data['data']
            else:
                return None
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return None

    # 피드로
    @staticmethod
    def add_remote(key, feed, remote_options_id):
        try:
            result = {}
            url = 'https://offcloud.com/api/remote'
            params = {
                'key' : key,
                'url' : feed.link,
                'remoteOptionId' : remote_options_id,
                'folderId' : feed.oc_folderid,
            }
            postdata = py_urllib.urlencode(params).encode('utf-8') 
            request = py_urllib2.Request(url, postdata)
            response = py_urllib2.urlopen(request)
            data = response.read()
            result = json.loads(data)
            logger.debug('ADD REMOTE ret: %s', result)
            if 'error' in result and result['error'].startswith("You have more than 100"):
                return 'over'
            feed.oc_requestId = result['requestId'] if 'requestId' in result else ''
            feed.oc_status = result['status'] if 'status' in result else ''
            feed.oc_createdOn =  result['createdOn'] if 'createdOn' in result else ''
            feed.oc_error = result['error'] if 'error' in result else ''
            feed.oc_json = result
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
  
    
    # 걍 마그넷으로
    @staticmethod
    def add_remote_by_magnet(key, magnet, remote_options_id, folder_id):
        try:
            url = 'https://offcloud.com/api/remote'
            params = {
                'key' : key,
                'url' : magnet,
                'remoteOptionId' : remote_options_id,
                'folderId' : folder_id,
            }
            postdata = py_urllib.urlencode(params).encode('utf-8')  
            request = py_urllib2.Request(url, postdata)
            response = py_urllib2.urlopen(request)
            data = response.read()
            result = json.loads(data)
            return result
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())


    @staticmethod
    def refresh_status(key, feed):
        try:
            url = 'https://offcloud.com/api/remote/status'
            params = {'key' : key, 'requestId' : feed.oc_requestId}
            postdata =py_urllib.urlencode(params).encode('utf-8')  
            request = py_urllib2.Request(url, postdata)
            response = py_urllib2.urlopen(request)
            data = response.read()
            data = json.loads(data)
            feed.oc_json = data
            if 'status' in data:
                feed.oc_status = data['status']['status']
                if feed.oc_status == 'error':
                    pass
                elif feed.oc_status == 'downloaded':
                    feed.oc_fileSize = int(data['status']['fileSize'])
                    feed.oc_fileName = data['status']['fileName']
            else:
                logger.debug('NO STATUS %s %s', url, params)
                feed.oc_status = 'NOSTATUS'
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
        
























    
    
    @staticmethod
    def retry(key, entity):
        try:
            url = 'https://offcloud.com/api/remote/retry/%s?key=%s' % (entity.requestId, key)
            request = py_urllib2.Request(url)
            response = py_urllib2.urlopen(request)
        except Exception as e:
            logger.debug('Exception:%s', e)
            logger.debug(traceback.format_exc())
            return None
    
    


    @staticmethod
    def cache(key, magnet_list, remoteOptionId):
        try:
            url = 'https://offcloud.com/api/torrent/check?key=%s' % (key)
            params = {'hashes' : magnet_list}
            res = requests.post(url, json=params)
            result = res.json()
            for i in result['cachedItems']:
                url = 'https://offcloud.com/api/remote'
                params = {
                    'key' : key,
                    'url' : 'magnet:?xt=urn:btih:%s' % i,
                    'remoteOptionId' : remoteOptionId,
                    'folderId' : '10b5Z-0RA08d6p2iMNQ9D__7e5gWOV6v5',
                }
                postdata = py_urllib.urlencode(params).encode('utf-8')  
                request = py_urllib2.Request(url, postdata)
                response = py_urllib2.urlopen(request)
                data = response.read()
                result = json.loads(data)
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return None