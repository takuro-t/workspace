#!/usr/bin/env python3
# coding: utf-8

import os
import sys
import argparse
from logging import getLogger, StreamHandler, Formatter, INFO, DEBUG
import trace
import traceback
import requests

tool_version = '20.5.8'     # change date

logger = getLogger(__name__)
handler = StreamHandler()
formatter = Formatter('%(asctime)s %(levelname)-7s %(message)s', '%Y/%m/%d %H:%M:%S')
handler.setFormatter(formatter)
handler.setLevel(INFO)
logger.setLevel(INFO)
logger.addHandler(handler)

class MyException(Exception):
    def __init__(self, msg=''):
        super().__init__()
        self.message = msg

class StrapiDocControl(object):
    def __init__(self, args, logger=None):
        self.logger = logger or getLogger(__name__)
        self.kind = args.kind
        self.version = args.ver
        self.doc_name = args.doc_name
        self.pub_name = args.pub_name or args.doc_name
        self.switch_dsp = args.switch_dsp
        self.strapi_base = args.host or 'xlibra2.kuukou.biz:11081'
        self.strapi = 'http://{}/doc-{}s'.format(self.strapi_base, args.kind)
        self.public_ed_url = 'http://xlibra2.kuukou.biz:8080/specification'
        self.public_id_url = 'http://xlibra2.kuukou.biz:8080/gitbook/JSA'
        self.contents = self.get_contents()

    def error(self, msg):
        self.logger.error(msg)

    def warning(self, msg):
        self.logger.warning(msg)

    def info(self, msg):
        self.logger.info(msg)

    def debug(self, msg):
        self.logger.debug(msg)

    def get_contents(self):
        res = requests.get(self.strapi)
        if res.status_code != 200:
            raise MyException('Incorrect request(code: {})'.format(res.status_code))
        j = res.json()
        self.debug(j)
        return j

    def is_exists(self, mode='doc'):
        if self.kind == 'ed':
            for j in self.contents:
                if self.version == j['ed_edition']: return True
            return False

        # kind == 'id'
        if mode == 'doc':
            for j in self.contents:
                if self.version != j['id_edition']: continue
                for i in j['id_list']:
                    if self.pub_name != i['doc_name']: continue
                    return True
                return False
            return False

        for j in self.contents:
            if self.version == j['id_edition']: return True
        return False

    def _request2register(self, item):
        res = requests.post(self.strapi, json=item)
        if res.status_code != 200:
            raise MyException('Incorrect request(code: {})'.format(res.status_code))
        self.info('Successful to register: %s' % res.json())

    def _request2modify(self, item, id):
        res = requests.put('{}/{}'.format(self.strapi, id), json=item)
        if res.status_code != 200:
            raise MyException('Incorrect request(code: {})'.format(res.status_code))
        self.info('Successful to modify: %s' % res.json())

    def _request2delete(self, id):
        res = requests.delete('{}/{}'.format(self.strapi, id))
        if res.status_code != 200:
            raise MyException('Incorrect request(code: {})'.format(res.status_code))
        self.info('Successful to delete')

    def get_target_version_dict(self):
        edition = '{}_edition'.format(self.kind)
        for c in self.contents:
            if c[edition] == self.version:
                return c
        return {}

    def display_content_ed(self):
        _dict = self.get_target_version_dict()
        if not _dict:
            raise MyException('{} is not found'.format(self.version))

        self.info('Display ED content: {}'.format(self.version))
        self.debug('dict: %s' % _dict)
        print(' {:12} {}'.format('id:', _dict['id']))
        print(' {:12} {}'.format('edition:', _dict['ed_edition']))
        print(' {:12} {}'.format('display:', _dict['switch_display']))
        print(' {:12} {}'.format('index_url:', _dict['ed_index_url']))

    def display_content_id(self):
        _dict = self.get_target_version_dict()
        if not _dict:
            raise MyException('{} is not found'.format(self.version))

        self.debug('dict: %s' % _dict)
        if not self.doc_name:
            self.info('Display ID content: {}'.format(self.version))
            print(' {:12} {}'.format('id:',_dict['id']))
            print(' {:12} {}'.format('edition:',_dict['id_edition']))
            print(' {:12} {}'.format('display:',_dict['switch_display']))
            print(' {:12} {}'.format('id_list', len(_dict['id_list'])))
            for i in _dict['id_list']:
                print('   {:10} {}'.format('doc_name:',i['doc_name']))
                print('   {:10} {}'.format('doc_url:',i['doc_url']))
            return

        self.info('Display ID content: {} of {}'.format(self.pub_name, self.version))
        for i in _dict['id_list']:
            name = i['doc_name']
            if name != self.pub_name: continue
            print(' {:12} {}'.format('doc_name:',name))
            print(' {:12} {}'.format('doc_url:',i['doc_url']))
            break
        return

    def display_content(self):
        eval('self.display_content_{}()'.format(self.kind))

    def update_content_ed(self):
        self.info('Update ED content: {}'.format(self.version))
        if self.is_exists():
            self.info('{} content is already exists. So skip the request'.format(self.version))
            return

        self.info('Register content to {}'.format(self.version))
        item = {'ed_edition':self.version, 'ed_index_url':'{}/{}/'.format(self.public_ed_url, self.version),
                'switch_display':self.switch_dsp}
        self.debug('item: %s' % item)
        self.info('Register content: {}'.format(self.version))
        self._request2register(item)
        return

    def _sorted_content_id(self, _lists):
        keys = list(map(lambda l:l['doc_name'], _lists))
        self.debug('Doc name list: %s' % keys)
        _list = []
        for key in sorted(keys):
            for d in _lists:
                if d['doc_name'] != key: continue
                _list.append(d)
                break
        return _list

    def update_content_id(self):
        if not self.doc_name:
            raise MyException('Incorrect parameter: DOC_NAME')

        self.info('Update ID content:{}, {}'.format(self.version, self.pub_name))
        if not self.is_exists(mode='version'):
            self.info('Register content to {}'.format(self.version))
            l = [{'doc_name':self.pub_name, 'doc_url':'{}/{}/{}/'.format(self.public_id_url, self.version, self.doc_name)}]
            item = {'id_edition':self.version, 'id_list':l, 'switch_display':self.switch_dsp}
            self.debug('item: %s' % item)
            self.info('Register content: {}'.format(self.pub_name))
            self._request2register(item)
            return

        self.info('Modify content to {}'.format(self.version))
        _dict = self.get_target_version_dict()
        if not _dict:
            raise MyException('{} is not found'.format(self.version))

        url = '{}/{}/{}/'.format(self.public_id_url, self.version, self.doc_name)
        _dict['switch_display'] = self.switch_dsp
        if not self.is_exists():
            l = {'doc_name':self.pub_name, 'doc_url':url}
            _dict['id_list'].append(l)
            _dict['id_list'] = self._sorted_content_id(_dict['id_list'])
            self.info('Register content: {}'.format(self.pub_name))
            self.debug('dict: %s' % _dict)
            self._request2modify(_dict, _dict['id'])
            return

        for d in _dict['id_list']:
            if d['doc_name'] != self.pub_name: continue
            d['doc_url'] = url
            break
        _dict['id_list'] = self._sorted_content_id(_dict['id_list'])
        self.info('Modify content: {}'.format(self.pub_name))
        self.debug('dict: %s' % _dict)
        self._request2modify(_dict, _dict['id'])
        return

    def update_content(self):
        eval('self.update_content_{}()'.format(self.kind))

    def delete_content(self):
        if self.kind == 'ed':
            self.warning('Delete function is for id')
            return

        if not self.doc_name:
            raise MyException('Incorrect parameter: DOC_NAME')

        _dict = self.get_target_version_dict()
        if not _dict:
            raise MyException('{} of {} is not found'.format(self.version, self.kind))

        for d in _dict['id_list']:
            if d['doc_name'] != self.pub_name: continue
            _dict['id_list'].remove(d)
            break
        self.info('Delete content: {}'.format(self.pub_name))
        self.debug('dict: %s' % _dict)
        self._request2modify(_dict, _dict['id'])
        return

    def undefine_content(self):
        _dict = self.get_target_version_dict()
        if not _dict:
            raise MyException('{} of {} is not found'.format(self.version, self.kind))
        self.info('Undefine content:{} of {}'.format(self.version, self.kind))
        self._request2delete(_dict['id'])

# end of class

def do_function(args):
    strapi = StrapiDocControl(args, logger)
    if args.function == 'update':
        strapi.update_content()
    elif args.function == 'delete':
        strapi.delete_content()
    elif args.function == 'undefine':
        strapi.undefine_content()
    else:
        strapi.display_content()

def parse_args():
    parser = argparse.ArgumentParser(description='Version %s\nThis script is...' % tool_version,
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('function', choices=['display', 'update', 'delete', 'undefine'],
                                    help='delete: remove DOC_NAME from VERSION\nundefine: remove VERSION')
    parser.add_argument('kind', choices=['ed', 'id'], help='kind of DOC tag')
    parser.add_argument('ver', metavar='VERSION', action='store', type=str, help='joined version')
    parser.add_argument('doc_name', metavar='DOC_NAME', action='store', type=str,
                                    nargs='?', default='', help='document name of public url')
    parser.add_argument('--public-name', dest='pub_name', metavar='NAME', action='store', type=str,
                                         default='', help='public doc name (Default: input doc_name value)')
    parser.add_argument('--no-dsp', dest='switch_dsp', action='store_false', default=True,
                                    help='not switch display mode (Default: display mode)')
    parser.add_argument('--host', dest='host', metavar='HOST[:PORT]', action='store', type=str,
                                  default='', help='connect url of strapi (Default: xspinach.kuukou.biz:10081)')
    parser.add_argument('--verbose', dest='verbose', action='store_true', default=False, help='verbose mode')
    parser.add_argument('--trace', dest='trace', action='store_true', default=False, help='trace mode')
    parser.add_argument('--version', action='version', version='Version: %s' % tool_version)

    args = parser.parse_args()
    return args

def main():
    args = parse_args()
    if args.verbose or args.trace:
        handler.setLevel(DEBUG)
        logger.setLevel(DEBUG)
        logger.addHandler(handler)
    logger.debug('args: %s' % args)
    try:
        if args.trace:
            tracer = trace.Trace(trace=True, count=True, ignoredirs=[sys.prefix, sys.exec_prefix])
            tracer.runfunc(do_function, args)
            sys.exit(0)

        do_function(args)
        logger.info('Completed to {} content'.format(args.function))
    except MyException as e:
        logger.error(e.message)
    except IOError:
        msg = sys.exc_info()[1]
        if 'Broken pipe' in msg:
            sys.exit(0)
        raise
    except:
        traceback.print_exc()

if __name__ == '__main__':
    main()

# vim: set ts=4 sw=4 et:
