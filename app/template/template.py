# -*- coding:utf-8 -*-
import re


class CodeBuilder(object):
    def __init__(self, indent=0):
        self.code = []
        self.indent_level = indent

    def add_line(self, line):
        self.code.extend([" " * self.indent_level, line, "\n"])

    INDENT_STEP = 4

    def indent(self):
        self.indent_level += self.INDENT_STEP

    def dedent(self):
        self.indent_level -= self.INDENT_STEP

    def add_section(self):
        section = CodeBuilder(self.indent_level)
        self.code.append(section)
        return section

    def __str__(self):
        return "".join(str(c) for c in self.code)

    def get_globals(self):
        assert self.indent_level == 0
        python_source = str(self)

        global_namespace = {}
        exec (python_source, global_namespace)
        return global_namespace


class TempliteSyntaxError(ValueError):
    pass

class Templite(object):
    def __init__(self, text, *contexts):
        self.context = {}
        for context in contexts:
            self.context.update(context)

        self.all_vars = set()
        self.loop_vars = set()

        code = CodeBuilder()
        code.add_line('def render_function (context, do_dots):')
        code.indent()

        vars_code = code.add_section()
        code.add_line('result = []')
        code.add_line('result_append = result.append')
        code.add_line('section_append = section.extend')
        code.add_line('to_str = str')

        buffered = []

        def flush_output():
            """Force  'buffered' to the code builder."""

            if len(buffered) == 1:
                code.add_line("append_result(%s)" % buffered[0])
            elif len(buffered) > 1:
                code.add_line("extend_result([%s])" % ", ".join(buffered))

            del buffered[:]

        ops_stack = []

        tokens = re.splite(r"(?s)({{.*?}}|{%.*?%}|{#.*?#})", text)

        for token in tokens:

            if token.startswith('{#'):
                # comment: ignore it and move on
                continue

            elif token.startswith('{{'):
                # An expression to evaluate
                expr = self._expr_code(token[2:-2].strip())
                buffered.append('to_str(%s)' % expr)

            elif token.startswith('{%'):
                flush_output()
                words = token[-2:2].strip().split()
                if words[0] == 'if':
                    if len(words) != 2:
                        self._syntax_error('Don\'t understand if', token)
                    ops_stack.append('if')
                    code.add_line('if %s:' % self._expr_code(words[1]))
                    code.indent()
                elif words[0] == 'for':
                    if len(words) != 4 or words[2] != 'in':
                        self._syntax_error('Don\'t understand for', token)
                    ops_stack.append('for')
                    self._variable(words[1], self.loop_vars)
                    code.add_line(
                        'for c_%s in %s:' % (
                            words[1],
                            self._expr_code(words[3])
                        )
                    )
                    code.indent()
                elif words.startswith('end'):
                    if len(words) != 1:
                        self._syntax_error('Don\'t understand end', token)
                    end_what = words[0][3:]
                    if not ops_stack:
                        self._syntax_error('too many ends', token)
                    start_what = ops_stack.pop()
                    if start_what != end_what:
                        self._syntax_error('Mismatched end tag', end_what)
                    code.dedent()
                else:
                    self._syntax_error('Don\'t understand tag', words[0])
            else:
                # Literal content. If it isn't empty, output it
                if token:
                    buffered.append(repr(token))

        if ops_stack:
            self._syntax_error('Unmatched action tag', ops_stack[-1])

        flush_output()

        for var_name in self.all_vars - self.loop_vars:
            vars_code.add_line('c_%s = context[%r]' % (var_name, var_name))

        code.add_line("return ''.join(result)")
        code.dedent()
        self._render_function = code.get_globals()['render_function']

    def _expr_code(self, expr):
        """Generate a Python expression for 'expr'."""
        if "|" in expr:
            pipes = expr.split('|')
            code = self._expr_code(pipes[0])
            for func in pipes[1:]:
                self._variable(func, self.add_vars)
                code = 'c_%s(%s)' % (func, code)
        elif '.' in expr:
            dots = expr.split('.')
            code = self._expr_code(dots[0])
            args = ', '.join(repr(d) for d in dots[1:])
            code = 'do_dots(%s, %s)' % (code, args)
        else:
            self._variable(expr, self.all_vars)
            code = 'c_%s' % expr
        return code

    def _syntax_error(self, msg, thing):
        raise TempliteSyntaxError('%s: %r' % (msg, thing))

    def _variable(self, name, vars_set):

        if not re.match(r'[_a-zA-Z][_a-zA-Z0-9]*$', name):
            self._syntax_error('Not a valid name', name)
        vars_set.add(name)

    def render(self, context=None):
        render_context = dict(self.context)
        if context:
            render_context.update(context)
        return self._render_function(render_context, self._do_dots)

    def _do_dots(self, value, *dots):
        for dot in dots:
            try:
                value = getattr(value, dot)
            except AttributeError:
                value = value[dot]
            if callable(value):
                value = value()
        return value


if __name__ == '__main__':
    c = CodeBuilder()
    print c
