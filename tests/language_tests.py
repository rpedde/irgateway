import os
import unittest
import yaml

import mock

from irgateway import lang


TESTDIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTSDIR = os.path.join(TESTDIR, 'language')


class TestLanguage(unittest.TestCase):
    def _run(self, test_definition):
        definition = os.path.join(SCRIPTSDIR, test_definition)
        rules = definition.split('.')[0] + '.rules'

        with open(definition, 'r') as f:
            config = yaml.load(f)

        tokenizer = lang.Tokenizer(rules)
        ast = lang.Parser(tokenizer).parse()

        # set up prereqs
        env = {}
        fenv = {}

        if 'setup' in config:
            env_setup = config['setup'].get('env', {})
            for k, v in env_setup.iteritems():
                env[k] = v
            fenv_setup = config['setup'].get('fenv', [])
            for k in fenv_setup:
                fenv[k] = mock.MagicMock()

        # run script
        ast.eval(env, fenv)

        print 'Resulting env: %s' % env

        # evaluate outcome
        if 'expectations' in config:
            expect = config['expectations'].get('env', {})
            print 'Env expectations: %s' % expect
            for k, v in expect.iteritems():
                assert env[k] == v


def generate(path):
    def generated(self):
        self._run(path)
    return generated

tlist = [x for x in os.listdir(SCRIPTSDIR) if x.endswith('.yml')]
for t in tlist:
    name = 'test_%s' % os.path.basename(t).split('.')[0]
    fn = generate(t)
    setattr(TestLanguage, name, fn)
