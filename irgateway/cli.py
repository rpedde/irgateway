#!/usr/bin/env python

import argparse
import logging
import sys
import yaml

import requests

from irgateway import events
from irgateway import lang
from irgateway import espeak


LOGGER = logging.getLogger(__name__)
SCRIPT_LOGGER = logging.getLogger('script')

CONFIG = None


def get_parser():
    cparser = argparse.ArgumentParser(
        add_help=False,
        description='common argument')

    cparser.add_argument('--config',
                         default='/etc/irdaemon.yml',
                         help='path to config file')
    cparser.add_argument('--debug', action='store_true',
                         help='debug mode')

    aparser = argparse.ArgumentParser(
        parents=[cparser], description='IR gateway')
    subparsers = aparser.add_subparsers(
        dest='action', help='action to perform')

    subparsers.add_parser('list', parents=[cparser],
                          help='list devices')

    subparsers.add_parser('run', parents=[cparser],
                          help='run in event loop')

    return aparser


def do_run():
    try:
        if 'device' in CONFIG:
            listener = events.EventListener(
                device_path=CONFIG['device'],
                exclusive=CONFIG.get('exclusive', False))
        elif 'device_match' in CONFIG:
            listener = events.EventListener(
                device_match=CONFIG['device_match'],
                exclusive=CONFIG.get('exclusive', False))
    except events.NoInputDevice:
        print >> sys.stdout, 'No input device'
        sys.exit(1)

    # set up the script
    ast = lang.Parser(lang.Tokenizer(CONFIG['rules'])).parse()

    env = {'action': 'initialize'}
    fenv = {'openhab': openhab,
            'printf': printf,
            'say': say}

    ast.eval(env, fenv)

    while True:
        for key, state in listener.get_events():
            LOGGER.debug('%s: %s' % (key, state))
            env['action'] = 'event'
            env['key'] = key
            env['state'] = state
            LOGGER.debug('Running event')
            ast.eval(env, fenv)
            LOGGER.debug('Event ran')

    return 0


def printf(fmt, *args):
    SCRIPT_LOGGER.info('********************')
    SCRIPT_LOGGER.info(fmt, *args)


def say(what):
    es = espeak.Espeak(voice=CONFIG.get('voice'))
    es.say(what)


def openhab(what, state):
    url = '%s/rest/items/%s' % (CONFIG['openhab'], what)
    headers = {'content-type': 'text/plain'}

    try:
        rv = requests.post(url, headers=headers,
                           data=state)
        if rv.status_code > 299:
            LOGGER.error('Error setting openhab value: (%s) %s' % (
                rv.status_code, rv.text))
            return False
        return True
    except Exception as e:
        LOGGER.error('Error communicating to openhab: %s' % e)

    return False


def main():
    global CONFIG

    parser = get_parser()
    args = parser.parse_args(sys.argv[1:])

    level = logging.INFO if not args.debug else logging.DEBUG
    logging.basicConfig(level=level)
    logging.getLogger('requests').setLevel(logging.WARN)
    logging.getLogger('urllib3').setLevel(logging.WARN)

    if args.action == 'list':
        events.EventListener.dump_inputs()
        sys.exit(0)

    with open(args.config, 'r') as f:
        CONFIG = yaml.load(f)

    if 'openhab' in CONFIG and CONFIG['openhab'].endswith('/'):
        CONFIG['openhab'] = CONFIG['openhab'][:-1]

    return do_run()

if __name__ == '__main__':
    sys.exit(main())
