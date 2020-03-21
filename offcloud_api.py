# -*- coding: utf-8 -*-
#########################################################
# python
import urllib
import urllib2
import traceback
import json
import logging

# third-party

# sjva 공용

# 패키지
from .plugin import logger, package_name
#########################################################

class Offcloud(object):

    @staticmethod
    def get_cache_list(key, magnet_list):
        try:
            url = 'https://offcloud.com/api/torrent/check?key=%s' % (key)
            params = {'hashes' : magnet_list}
            import requests
            res = requests.post(url, json=params)
            result = res.json()
            
            return result['cachedItems']
        except Exception as e:
            logger.debug('Exception:%s', e)
            logger.debug(traceback.format_exc())
            return None 


    @staticmethod
    def get_remote_account(key):
        try:
            logger.debug('get_remote_account : %s', key)
            url = 'https://offcloud.com/api/remote/accounts'
            params = {'key' : key}
            postdata = urllib.urlencode(params) 
            request = urllib2.Request(url, postdata)
            response = urllib2.urlopen(request)
            data = json.load(response)
            logger.debug(data)
            if 'data' in data:
                return data['data']
            else:
                return None
        except Exception as e:
            logger.debug('Exception:%s', e)
            logger.debug(traceback.format_exc())
            return None

    # 피드로
    @staticmethod
    def add_remote(key, feed, remote_options_id):
        try:
            result = {}
            #logger.debug('add_remote : %s', remote_options_id)
            #logger.debug('add_remote entity: %s', feed)

            url = 'https://offcloud.com/api/remote'
            params = {
                'key' : key,
                'url' : feed.link,
                'remoteOptionId' : remote_options_id,
                'folderId' : feed.oc_folderid,
            }
            postdata = urllib.urlencode( params ) 
            request = urllib2.Request(url, postdata)
            response = urllib2.urlopen(request)
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
            """
            feed.site = result['site'] if 'site' in result else ''
            feed.fileName = result['fileName'] if 'fileName' in result else ''
            feed.originalLink = result['originalLink'] if 'originalLink' in result else ''
            """
        except Exception as e:
            logger.debug('Exception:%s', e)
            logger.debug(traceback.format_exc())
  
    
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
            postdata = urllib.urlencode( params ) 
            request = urllib2.Request(url, postdata)
            response = urllib2.urlopen(request)
            data = response.read()
            result = json.loads(data)
            return result
        except Exception as e:
            logger.debug('Exception:%s', e)
            logger.debug(traceback.format_exc())


    @staticmethod
    def refresh_status(key, feed):
        try:
            url = 'https://offcloud.com/api/remote/status'
            params = {'key' : key, 'requestId' : feed.oc_requestId}
            postdata = urllib.urlencode( params ) 
            request = urllib2.Request(url, postdata)
            response = urllib2.urlopen(request)
            data = response.read()
            data = json.loads(data)
            feed.oc_json = data
            #logger.debug(feed.oc_json)
            if 'status' in data:
                feed.oc_status = data['status']['status']
                if feed.oc_status == 'error':
                    #Offcloud.retry(key, entity)
                    #entity.retry_count += 1
                    pass
                elif feed.oc_status == 'downloaded':
                    feed.oc_fileSize = int(data['status']['fileSize'])
                    feed.oc_fileName = data['status']['fileName']
            else:
                logger.debug('NO STATUS %s %s', url, params)
                feed.oc_status = 'NOSTATUS'
            #else:
            #    if entity.status == 'error':
            #        Offcloud.retry(key, entity)
            #        entity.retry += 1

        except Exception as e:
            logger.debug('Exception:%s', e)
            logger.debug(traceback.format_exc())
            #entity.exception = '%s' % e
        

























    """
    @staticmethod
    def add_remote(key, feed, is_update=False):
        try:
            result = {}
            logger.debug('add_remote : %s', key)
            logger.debug('add_remote entity: %s', entity)

            url = 'https://offcloud.com/api/remote'
            params = {
                'key' : key,
                'url' : entity.request_link,
                'remoteOptionId' : entity.remoteOptionId,
                'folderId' : entity.folderid,
            }
            postdata = urllib.urlencode( params ) 
            request = urllib2.Request(url, postdata)
            response = urllib2.urlopen(request)
            data = response.read()
            logger.debug('ADD : %s', data)
            #result = json.load(response)
            result = json.loads(data)
            logger.debug('ADD REMOTE ret: %s', result)

            entity.requestId = result['requestId'] if 'requestId' in result else ''
            entity.status = result['status'] if 'status' in result else ''
            entity.createdOn =  result['createdOn'] if 'createdOn' in result else ''
            entity.site = result['site'] if 'site' in result else ''
            entity.fileName = result['fileName'] if 'fileName' in result else ''
            entity.originalLink = result['originalLink'] if 'originalLink' in result else ''
            entity.error = result['error'] if 'error' in result else ''

        except Exception as e:
            logger.debug('Exception:%s', e)
            logger.debug(traceback.format_exc())
            entity.exception = '%s' % e
        finally:
            if is_update:
                DB.update(entity)
            else:
                DB.insert(entity)
    """
    
    
    @staticmethod
    def retry(key, entity):
        try:
            logger.debug('retry : %s', entity.entry_title)
            url = 'https://offcloud.com/api/remote/retry/%s?key=%s' % (entity.requestId, key)
            request = urllib2.Request(url)
            response = urllib2.urlopen(request)
            logger.debug(url)
            logger.debug(response.read())

            #data = json.load(response)
            #logger.debug(data)
            #entity.status = data['status']['status']
            #entity.error = data['status']
            #if entity.status == 'error':
                

        except Exception as e:
            logger.debug('Exception:%s', e)
            logger.debug(traceback.format_exc())
            return None
    
    



    @staticmethod
    def cache(key, magnet_list, remoteOptionId):
        try:
            
            #url = 'https://offcloud.com/api/cache?key=%s' % (key)
            url = 'https://offcloud.com/api/torrent/check?key=%s' % (key)

            #curl -X "POST" "https://offcloud.com/api/torrent/check?apikey=2Gts0NRMZpdznCbwPPGoDP4kND6QLH5w" -H 'Content-Type: application/json' -d $'{"hashes": ["b6ed43c90bb5699c7a2f5e5453d681436847791a", "f223ab10189810f6aa5fdecc696bf4621ba945b0", "19bc721d2573fd719860e3d6a325f24e700f562a"]}'

            #d = {}
            #d['hashes'] = 
            params = {'hashes' : magnet_list}
            #params = 
            """
            postdata = urllib.urlencode( params ).encode()
            #postdata = urllib.urlencode(d)
            request = urllib2.Request(url, postdata)
            response = urllib2.urlopen(request)

            logger.debug(url)
            logger.debug(response.read())
            #data = json.load(response)
            #logger.debug(data)
            """
            import requests
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
                postdata = urllib.urlencode( params ) 
                request = urllib2.Request(url, postdata)
                response = urllib2.urlopen(request)
                data = response.read()
                logger.debug('ADD : %s', data)
                #result = json.load(response)
                result = json.loads(data)
                logger.debug('ADD REMOTE ret: %s', result)




            #entity.status = data['status']['status']
            #entity.error = data['status']
            #if entity.status == 'error':
                

        except Exception as e:
            logger.debug('Exception:%s', e)
            logger.debug(traceback.format_exc())
            return None