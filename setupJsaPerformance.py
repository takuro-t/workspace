#!/usr/bin/env python
# encoding: utf-8

import os
import sys
from logging import getLogger, StreamHandler, Formatter, INFO, DEBUG

tool_version = '20.4.16'    # Change date

logger = getLogger(__name__)
handler = StreamHandler()
formatter = Formatter('%(asctime)s %(levelname)-7s %(message)s', '%Y/%m/%d %H:%M:%S')
handler.setFormatter(formatter)
handler.setLevel(INFO)
logger.setLevel(INFO)
logger.addHandler(handler)

class ChangeEnvironment(object):
    def __init__(self, cell, node, server, dryrun=False):
        self.cell_name = cell
        self.node_name = node
        self.server_name = server
        self.dryrun = dryrun
        self.cell_id = AdminConfig.getid('/Cell:%s/' % self.cell_name)
        self.node_id = AdminConfig.getid('/Node:%s/' % self.node_name)
        self.server_id = AdminConfig.getid('/Node:%s/Server:%s/' % \
                         (self.node_name, self.server_name))
        if not self.server_id:
            logger.error('%s is not exists' % self.server_name)
            sys.exit(1)

        self.search_key = {'J2CActivationSpec':'name',
                           'JAASAuthData':'alias',
                           'DataSource':'name',
                           'CMPConnectorFactory':'name',
                           'J2EEResourceProperty':'name'}

        self.jdbc_dict = {'provider'   : 'Oracle JDBC Driver (XA)',
                          'datasource' : 'oracle',
                          'property'   : ['mapping'],
                          'resource'   : ['URL']}
        self.xcygnus_url = 'xcygnus'
        self.xpollux_url = 'xpollux'


    def get_entity_dict(self, id, entity_name, filter_list=[]):
        logger.debug('id: %s, entity_name: %s, filter: %s' % (id, entity_name, filter_list))
        items = AdminConfig.list(entity_name, id).split(java.lang.System.getProperty('line.separator'))
        _dict = {}
        if not items: return _dict
        for i in items:
            name = AdminConfig.showAttribute(i, self.search_key[entity_name])
            if filter_list:
                if not name in filter_list: continue
            _dict[name] = i
        return _dict

    def get_entity(self, id, entity_name, keyword):
        logger.debug('entity_name: %s, search_keyword: %s' % (entity_name, keyword))
        entity_dict = self.get_entity_dict(id, entity_name)
        logger.debug('entity: %s' % entity_dict)
        if not entity_dict: return None
        if not keyword in entity_dict: return None
        return entity_dict[keyword]

    def get_j2c_dict(self):
        _dict = self.get_entity_dict(self.cell_id, 'JAASAuthData')
        _d = {}
        for k in _dict.keys():
            logger.debug('Search j2c: %s' % k)
            s = k.split('/')
            n = s[1]
            if n == 'connectoracle':
                _d['itb'] = k
            elif n == 'connectoracle_pt':
                _d['pt'] = k
        logger.debug(_d)
        return _d

    def show_authDataAlias(self):
        ora_entity = self.get_entity(self.server_id, 'DataSource', 'oracle')
        authDataAlias = AdminConfig.showAttribute(ora_entity, 'authDataAlias')
        logger.info('Show authDataAlias: %s' % authDataAlias)

    def show_url(self):
        datasource = self.get_entity(self.server_id, 'DataSource', 'oracle')
        resource = self.get_entity(datasource, 'J2EEResourceProperty', 'URL')
        url = AdminConfig.showAttribute(resource, 'value')
        logger.info('Show URL: %s' % url)

    def save_config(self):
        if self.dryrun:
            logger.info('Not save mode')
            return
        AdminConfig.save()
        return

    def modify_datasource_auth(self, j2c_name):
        logger.info('Modify authDataAlias of ConnectFactory to %s' % j2c_name)
        opt = '[name "oracle_CF"] [authDataAlias %s]' % j2c_name
        logger.debug('modify cmp opt: %s' % opt)
        factory = self.get_entity(self.server_id, 'CMPConnectorFactory', 'oracle_CF')
        AdminConfig.modify(factory, '[%s]' % opt)

        logger.info('Modify authDataAlias of MappingModule to %s' % j2c_name)
        opt = '[authDataAlias %s] [mappingConfigAlias DefaultPrincipalMapping]' % j2c_name 
        logger.debug('modify mapping opt: %s' % opt)
        datasource = self.get_entity(self.server_id, 'DataSource', 'oracle')
        AdminConfig.create('MappingModule', datasource, '[%s]' % opt)

        logger.info('Modify authDataAlias of DataSource to %s ' % j2c_name)
        opt = '[authDataAlias %s]' % j2c_name
        logger.debug('modifyDatasource opt: %s' % opt)
        AdminConfig.modify(datasource, '[%s]' % opt)

        self.save_config()
        logger.info('Successful to modify authDataAlias')

    def modify_datasource_url(self, url):
        logger.info('Modify URL')
        opt = '[name "URL"] [value "%s"]' % url
        logger.debug('modify URL opt: %s' % opt)
        datasource = self.get_entity(self.server_id, 'DataSource', 'oracle')
        resource = self.get_entity(datasource, 'J2EEResourceProperty', 'URL')
        AdminConfig.modify(resource, '[%s]' % opt)

        self.save_config()
        logger.info('Successful to modify URL')

    def change_pt(self):
        _dict = self.get_j2c_dict()
        self.modify_datasource_auth(_dict['pt'])
        self.show_authDataAlias()

    def change_itb(self):
        _dict = self.get_j2c_dict()
        self.modify_datasource_auth(_dict['itb'])
        self.show_authDataAlias()

    def change_xcygnus(self):
        self.modify_datasource_url(self.xcygnus_url)
        self.show_url()

    def change_xpollux(self):
        self.modify_datasource_url(self.xpollux_url)
        self.show_url()

    def show(self):
        self.show_authDataAlias()
        self.show_url()


# <-- end of class


def usage():
    print """
    Version: %s

    usage: wsadmin -f setupJsaPerformance.py FUNCTION [SERVER_NAME] [debug] [FUNC] [help]

    FUNCTION:       pt (change to connectoracle_pt)
                    itb (change to connectoracle)
                    xcygnus (change to URL of xcygnus)
                    xpollux (change to URL of xpollux)
                    show (display authuser & URL)
    SERVER_NAME     server1 | server2 (Default: server1)
    debug:          debug mode 
    FUNC:           internal function run
    help:           this message

    """ % (tool_version)

def get_parameter():
    _args = {'function':sys.argv[0], 'server_name':'server1',
             'debug':False, 'dryrun':False, 'test':False}
    if not sys.argv:
        return _args

    for a in sys.argv:
        if 'debug' in a:
            _args['debug'] = True
            continue
        if 'server' in a:
            _args['server_name'] = a 
            continue
        if 'dryrun' in a:
            _args['dryrun'] = True
            continue
        if 'testmode' in a:
            _args['test'] = a 
            continue
        if 'help' in a:
            usage()
            sys.exit(0)
        _args['func'] = a
    return _args

def validate_parameters():
    if not sys.argv:
        logger.error('Incorrect parameter')
        usage()
        return False
    func = sys.argv[0]
    if not func in ['pt', 'itb', 'xcygnus', 'xpollux', 'show']:
        logger.error('Incorrect parameter')
        usage()
        return False
    return True

def main():
    if not validate_parameters():
        sys.exit(1)

    args = get_parameter()
    if args['debug']:
        handler.setLevel(DEBUG)
        logger.setLevel(DEBUG)
        logger.addHandler(handler)
    logger.debug('args: %s' % args)

    cell_name = AdminControl.getCell()
    node_name = AdminControl.getNode()
    logger.debug('cell: %s, node: %s, server: %s' % (cell_name, node_name, args['server_name']))

    chenv = ChangeEnvironment(cell_name, node_name, args['server_name'], args['dryrun'])
    if args['test']:
        eval('chenv.%s()' % args['func'])
        sys.exit(0)

    function = args['function']
    if function in ['pt', 'itb']:
        logger.info('Change authDataAlias for %s' % function.upper())
        eval('chenv.change_%s()' % function)
        logger.info('Completed to change authDataAlias')
    elif function in ['xcygnus', 'xpollux']:
        logger.info('Change URL to %s' % function)
        eval('chenv.change_%s()' % function)
        logger.info('Completed to change URL')
    else:
        chenv.show()

if __name__ == '__main__':
    main()

# vim: set ts=4 sw=4 et:
