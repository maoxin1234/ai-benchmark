"""Runelet 表达式求值器 参考实现。递归下降解析 + 递归求值。"""
import sys


def tokenize(s):
    toks, i, n = [], 0, len(s)
    kw = {'let', 'in', 'if', 'then', 'else', 'interleave', 'times'}
    while i < n:
        c = s[i]
        if c.isspace():
            i += 1; continue
        if c == '"':
            j = i + 1; buf = ''
            while j < n and s[j] != '"':
                buf += s[j]; j += 1
            if j >= n:
                raise SyntaxError('unterminated')
            toks.append(('STR', buf)); i = j + 1; continue
        if c.isdigit():
            j = i
            while j < n and s[j].isdigit():
                j += 1
            toks.append(('NUM', int(s[i:j]))); i = j; continue
        if c.isalpha() or c == '_':
            j = i
            while j < n and (s[j].isalnum() or s[j] == '_'):
                j += 1
            w = s[i:j]
            toks.append((w if w in kw else 'IDENT', w)); i = j; continue
        if s[i:i + 2] in ('==', '!=', '<=', '>='):
            toks.append(('OP', s[i:i + 2])); i += 2; continue
        if c in '+-*/%<>':
            toks.append(('OP', c)); i += 1; continue
        if c == '(':  toks.append(('LP', c)); i += 1; continue
        if c == ')':  toks.append(('RP', c)); i += 1; continue
        if c == ',':  toks.append(('COMMA', c)); i += 1; continue
        if c == '=':  toks.append(('EQ', c)); i += 1; continue
        raise SyntaxError(f'bad char {c}')
    toks.append(('EOF', None))
    return toks


class Parser:
    def __init__(self, toks):
        self.toks = toks; self.pos = 0

    def peek(self): return self.toks[self.pos]

    def nxt(self):
        t = self.toks[self.pos]; self.pos += 1; return t

    def expect(self, kind):
        t = self.nxt()
        if t[0] != kind:
            raise SyntaxError(f'expected {kind}')
        return t

    def parse(self):
        e = self.expr()
        if self.peek()[0] != 'EOF':
            raise SyntaxError('trailing')
        return e

    def expr(self):
        t = self.peek()
        if t[0] == 'let':
            self.nxt(); name = self.expect('IDENT')[1]; self.expect('EQ')
            val = self.expr(); self.expect('in'); body = self.expr()
            return ('let', name, val, body)
        if t[0] == 'if':
            self.nxt(); cond = self.expr(); self.expect('then')
            a = self.expr(); self.expect('else'); b = self.expr()
            return ('if', cond, a, b)
        return self.compare()

    def compare(self):
        left = self.addsub()
        t = self.peek()
        if t[0] == 'OP' and t[1] in ('==', '!=', '<', '>', '<=', '>='):
            self.nxt(); right = self.addsub()
            return ('cmp', t[1], left, right)
        return left

    def addsub(self):
        left = self.muldiv()
        while self.peek()[0] == 'OP' and self.peek()[1] in ('+', '-'):
            op = self.nxt()[1]; left = ('bin', op, left, self.muldiv())
        return left

    def muldiv(self):
        left = self.atom()
        while self.peek()[0] == 'OP' and self.peek()[1] in ('*', '/', '%'):
            op = self.nxt()[1]; left = ('bin', op, left, self.atom())
        return left

    def atom(self):
        t = self.peek()
        if t[0] == 'NUM': self.nxt(); return ('num', t[1])
        if t[0] == 'STR': self.nxt(); return ('str', t[1])
        if t[0] in ('interleave', 'times'):
            self.nxt(); self.expect('LP'); a = self.expr()
            self.expect('COMMA'); b = self.expr(); self.expect('RP')
            return ('call', t[0], a, b)
        if t[0] == 'IDENT': self.nxt(); return ('var', t[1])
        if t[0] == 'LP':
            self.nxt(); e = self.expr(); self.expect('RP'); return e
        raise SyntaxError('unexpected')


def is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def ev(node, env):
    t = node[0]
    if t == 'num': return node[1]
    if t == 'str': return node[1]
    if t == 'var':
        if node[1] not in env:
            raise NameError(node[1])
        return env[node[1]]
    if t == 'let':
        _, name, ve, body = node
        e2 = dict(env); e2[name] = ev(ve, env)
        return ev(body, e2)
    if t == 'if':
        _, c, a, b = node
        cv = ev(c, env)
        if not isinstance(cv, bool):
            raise TypeError('cond')
        return ev(a, env) if cv else ev(b, env)
    if t == 'bin':
        _, op, l, r = node
        a, b = ev(l, env), ev(r, env)
        if not (is_int(a) and is_int(b)):
            raise TypeError('arith')
        if op == '+': return a + b
        if op == '-': return a - b
        if op == '*': return a * b
        if op == '/': return a // b      # b==0 -> ZeroDivisionError
        if op == '%': return a % b
    if t == 'cmp':
        _, op, l, r = node
        a, b = ev(l, env), ev(r, env)
        if op in ('==', '!='):
            res = (type(a) == type(b)) and (a == b)
            return res if op == '==' else not res
        if not (is_int(a) and is_int(b)):
            raise TypeError('cmp')
        if op == '<':  return a < b
        if op == '>':  return a > b
        if op == '<=': return a <= b
        if op == '>=': return a >= b
    if t == 'call':
        _, fn, ae, be = node
        a, b = ev(ae, env), ev(be, env)
        if fn == 'interleave':
            if not (isinstance(a, str) and isinstance(b, str)):
                raise TypeError
            res, i = [], 0
            while i < len(a) or i < len(b):
                if i < len(a): res.append(a[i])
                if i < len(b): res.append(b[i])
                i += 1
            return ''.join(res)
        if fn == 'times':
            if not (isinstance(a, str) and is_int(b)):
                raise TypeError
            if b < 0:
                raise ValueError
            return a * b
    raise RuntimeError('unknown node')


def fmt(v):
    if isinstance(v, bool): return 'true' if v else 'false'
    if isinstance(v, int):  return str(v)
    if isinstance(v, str):  return v
    raise TypeError


def main():
    for line in sys.stdin:
        line = line.rstrip('\n')
        if line.strip() == '':
            continue
        try:
            ast = Parser(tokenize(line)).parse()
            print(fmt(ev(ast, {})))
        except Exception:
            print('ERROR')


main()
