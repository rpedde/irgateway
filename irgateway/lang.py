import logging
import operator
import shlex
import sys

LOGGER = logging.getLogger(__name__)


class Tokenizer(shlex.shlex):
    def __init__(self, path):
        self.path = path
        self.fp = open(self.path, 'r')

        shlex.shlex.__init__(self, self.fp, self.path)

    def tokens(self):
        result = []
        while True:
            val = self.get_token()
            if val:
                result.append(val)
            else:
                break

        return result

    def peek_token(self, items=1):
        tokenlist = []
        for _ in range(items):
            tokenlist.append(self.get_token())

        for item in reversed(tokenlist):
            self.push_token(item)

        if items == 1:
            return tokenlist[0]

        return tokenlist

    def pop_token(self):
        return self.get_token()


def oper_and(env, fenv, v1, v2):
    return v1.eval(env, fenv) and v2.eval(env, fenv)


def oper_or(env, fenv, v1, v2):
    return v1.eval(env, fenv) or v2.eval(env, fenv)


def oper_assign(env, fenv, v1, v2):
    result = v2.eval(env, fenv)
    env[v1.value] = result
    return result


class Node(object):
    BLOCK = 'block'
    IF = 'if statement'
    STRING = 'string literal'
    NUMBER = 'numeric literal'
    SYMBOL = 'symbol'
    BINOP = 'binary operator'
    FN = 'function'

    LVALUES = [STRING, NUMBER]
    VALUES = [STRING, NUMBER, SYMBOL]

    BINOPS = {
        '/': {'op': operator.div},
        '*': {'op': operator.mul},
        '+': {'op': operator.add},
        '-': {'op': operator.sub},
        '=': {'op': oper_assign, 'native': True},
        '>': {'op': operator.gt},
        '<': {'op': operator.lt},
        '<=': {'op': operator.le},
        '>=': {'op': operator.ge},
        '==': {'op': operator.eq},
        'and': {'op': oper_and, 'native': True},
        'or': {'op': oper_or, 'native': True}
    }

    def __init__(self, type, value):
        self.type = type
        self.value = value

    def dot(self, file):
        with open(file, 'w') as fd:
            fd.write("digraph G {\n")
            self._emit_dot(fd)
            fd.write("}")

    def _emit_dot(self, fd):
        fd.write('/* Node %s (%s) */\n' % (id(self), self.type))

        if self.type == Node.BLOCK:
            fd.write('%s [shape="record" label="<HEAD> BLOCK | %s "];\n' % (
                id(self), ' | '.join(['<ptr%s> STMT' % id(x)
                                      for x in self.value])))

            for x in self.value:
                fd.write('%s:ptr%s -> %s\n' % (
                    id(self), id(x), id(x)))
                x._emit_dot(fd)

        if self.type == Node.IF:
            fd.write('%s [shape="record" label="<HEAD> '
                     'IF | <ptr%s> EXPR | <then> THEN | <ptr%s> BLOCK' % (
                         id(self), id(self.value[0]), id(self.value[1])))
            if self.value[2]:
                fd.write(' | <else> ELSE | <ptr%s> BLOCK' % id(self.value[2]))
            fd.write('"]\n')

            fd.write("%s:ptr%s -> %s" % (
                id(self), id(self.value[0]), id(self.value[0])))
            self.value[0]._emit_dot(fd)
            fd.write("%s:ptr%s -> %s" % (
                id(self), id(self.value[1]), id(self.value[1])))
            self.value[1]._emit_dot(fd)

            if self.value[2]:
                fd.write("%s:ptr%s -> %s" % (
                    id(self), id(self.value[2]), id(self.value[2])))
                self.value[2]._emit_dot(fd)
        if self.type == Node.FN:
            fd.write('%s [shape="record" label="<HEAD> CALL | %s' % (
                id(self), self.value[0]))
            if len(self.value[1]):
                fd.write(' | ')
                fd.write(' | '.join(['<ptr%s> EXPR' % id(x)
                                     for x in self.value[1]]))
            fd.write('"]\n')

            for x in self.value[1]:
                fd.write('%s:ptr%s -> %s' % (
                    id(self), id(x), id(x)))
                x._emit_dot(fd)

        if self.type == Node.BINOP:
            fd.write('%s [label="%s"]\n' % (
                id(self), self.value[0]))
            fd.write('%s -> %s\n' % (id(self), id(self.value[1])))
            fd.write('%s -> %s\n' % (id(self), id(self.value[2])))
            self.value[1]._emit_dot(fd)
            self.value[2]._emit_dot(fd)

        if self.type in [self.STRING, self.NUMBER, self.SYMBOL]:
            fd.write('%s [label="%s: %s"]\n' % (
                id(self), self.type, self.value))

        fd.write('/* End node %s */\n' % id(self))

    def eval(self, env, fenv):
        if self.type == self.BLOCK:
            for item in self.value:
                retval = item.eval(env, fenv)
            return retval
        if self.type == self.IF:
            if self.value[0].eval(env, fenv):
                return self.value[1].eval(env, fenv)
            else:
                if self.value[2]:
                    return self.value[2].eval(env, fenv)
                else:
                    return None
        if self.type == self.BINOP:
            op = self.BINOPS[self.value[0]]['op']
            native = self.BINOPS[self.value[0]].get('native', False)

            if not native:
                arg1 = self.value[1].eval(env, fenv)
                arg2 = self.value[2].eval(env, fenv)
                return op(arg1, arg2)
            else:
                return op(env, fenv, self.value[1], self.value[2])
        if self.type in self.LVALUES:
            return self.value
        if self.type == self.SYMBOL:
            if self.value not in env:
                raise RuntimeError('unknown variable: %s' % self.value)
            return env[self.value]
        if self.type == self.FN:
            if not self.value[0] in fenv:
                raise RuntimeError('cannot find function: %s' % self.value[0])
            args = [x.eval(env, fenv) for x in self.value[1]]
            return fenv[self.value[0]](*args)


class Parser(object):
    RESERVED = ['if', 'else', 'and', 'or']

    def __init__(self, tokenizer):
        self.tokenizer = tokenizer

    def pop(self):
        return self.tokenizer.pop_token()

    def push(self):
        return self.tokenizer.push_token()

    def peek(self, items=1):
        return self.tokenizer.peek_token(items)

    def parse(self):
        ast = self.parse_program()
        return ast

    def check_symbol(self, value):
        if not value[0].isalpha():
            raise RuntimeError('Valid variables start with letter: %s',
                               value)

        if not value.isalnum():
            raise RuntimeError('Valid variables must be alphanumeric: %s',
                               value)

        if value in self.RESERVED:
            raise RuntimeError('Cannot use reserved word for variable: %s',
                               value)

    def parse_program(self):
        LOGGER.debug('Parsing program: %s', self.peek())

        block = []

        token = self.peek()
        while token != '':
            block += self.parse_program_block().value
            token = self.peek()

        return Node(Node.BLOCK, block)

    def parse_program_block(self):
        LOGGER.debug('Parsing program block: %s', self.peek())

        block = []

        token = self.peek()

        if token == '{':
            LOGGER.debug('found braced block')
            self.pop()
            while True:
                LOGGER.debug('getting next in braced block')
                block += self.parse_program_block().value
                if self.peek() == '}':
                    self.pop()
                    LOGGER.debug('ended braced block: len %s', len(block))
                    return Node(Node.BLOCK, block)

                if self.peek() == '':
                    raise RuntimeError('Expecting "}"')

            return Node(Node.BLOCK, block)

        LOGGER.debug('No braced block')
        result = self.parse_statement()
        LOGGER.debug('unbraced block parsed')
        return Node(Node.BLOCK, [result])

    def parse_statement(self):
        LOGGER.debug('parsing statement: %s' % self.peek())
        token = self.peek()
        if token == 'if':
            self.pop()
            LOGGER.debug('IF statement')
            else_block = None
            if self.pop() != '(':
                raise RuntimeError('Expecting "("')
            expression = self.parse_expression()
            if self.pop() != ')':
                raise RuntimeError('Expecting ")"')
            if_block = self.parse_program_block()
            if self.peek() == 'else':
                self.pop()
                else_block = self.parse_program_block()
            return Node(Node.IF, (expression, if_block, else_block))
        return self.parse_expression()

    def parse_expression(self):
        LOGGER.debug('parsing expression: %s', self.peek())
        if self.peek() == '(':
            self.pop()
            value = self.parse_expression()
            if self.pop() != ')':
                raise SyntaxError('Expecting ")"')
            LOGGER.debug('got parenthesized expression.. next: %s' % self.peek())
        else:
            value = self.parse_term()

        while True:
            token1, token2 = self.peek(2)
            bigtoken = '%s%s' % (token1, token2)

            if bigtoken in Node.BINOPS or token1 in Node.BINOPS:
                if bigtoken in Node.BINOPS:
                    self.pop()
                    self.pop()
                    token = bigtoken
                else:
                    token = self.pop()

                othervalue = self.parse_expression()
                LOGGER.debug('parsed as binary op (%s %s %s)' % (
                    value.type, token, othervalue.type))

                return Node(Node.BINOP, (token, value, othervalue))
            else:
                return value

    def parse_term(self):
        value = self.parse_value()
        # function
        if value.type == Node.SYMBOL and self.peek() == '(':
            self.pop()
            fn = value.value
            args = []
            while self.peek() != ')':
                if self.peek() == '':
                    raise SyntaxError('Expecting ")"')
                args.append(self.parse_expression())
                if self.peek() == ',':
                    self.pop()

            LOGGER.debug('parsed expression as function')
            self.pop()
            return Node(Node.FN, (fn, args))
        LOGGER.debug('parsed as bare value')
        return value

    def parse_value(self):
        LOGGER.debug('parsing value: %s', self.peek())
        token = self.pop()
        if token.startswith('"') and token.endswith('"'):
            value = token[1:-1]

            LOGGER.debug('parsed as literal string "%s"' % value)
            return Node(Node.STRING, value)
        try:
            if str(int(token)) == token:
                LOGGER.debug('parsed as numeric: %s' % token)
                return Node(Node.NUMBER, int(token))
        except:
            pass

        LOGGER.debug('parsed as symbol: %s' % token)
        self.check_symbol(token)
        return Node(Node.SYMBOL, token)


def main(rawargs):
    logging.basicConfig(level=logging.DEBUG)
    path = '../sample.rules' if not len(rawargs) else rawargs[0]

    tokenizer = Tokenizer(path)
    print tokenizer.tokens()

    tokenizer = Tokenizer(path)
    parser = Parser(tokenizer)

    ast = parser.parse()

    ast.dot('out.dot')

    def env_printf(fmt, *args):
        sys.stdout.write(fmt % args)

    env = {'action': 'event', 'key': '1'}
    fenv = {'printf': env_printf}

    result = ast.eval(env, fenv)
    print 'Result of execution: %s' % result

if __name__ == '__main__':
    main(sys.argv[1:])
