import re
import typing as t
from textwrap import dedent
from textwrap import indent

import black
import libcst as cst

_re_leading_spaces = re.compile(r'^ *')


def fixture(code: str):
    module = cst.parse_module(code)
    
    _flag = 'ready'
    _indent = -1
    
    def walk(node):
        nonlocal _flag, _indent
        _indent += 1
        
        for item in node.body:
            if isinstance(item, cst.Import):
                _flag = 'observing_imports'
            else:
                if _flag == 'observing_imports':
                    if item.leading_lines:
                        # there are blank line(s) between imports and other \
                        # statements.
                        _flag = 'ready'
        
        _indent -= 1
    
    for item in module.body:
        pass


def ensure_trailing_newline(code: str) -> str:
    if not code.endswith('\n'):
        code += '\n'
    return code


def join_oneline_if_stmt(code: str) -> str:
    """
    before:
        if x:
            return 1
    after:
        if x: return 1
    """
    
    def walk() -> t.Iterator[str]:
        flag = False
        for l0, l1, l2, l3, l4 in _continous_window(code.splitlines(), 5):
            if flag:
                flag = False
                continue
            if l0.lstrip().startswith('if '):
                if l1 and len(l1) < 20 and not l1.lstrip().startswith('if '):
                    i0, i1, i2, i3, i4 = tuple(
                        map(
                            len,
                            (
                                _re_leading_spaces.match(x).group()
                                for x in (l0, l1, l2, l3, l4)
                            ),
                        )
                    )
                    if i0 < i1:
                        if (
                            (l2 and i2 < i1)
                            or (l3 and i3 < i1)
                            or (l4 and i4 < i1)
                        ):
                            out = '{} {}'.format(l0, l1.lstrip())
                            if len(out) < 80:
                                flag = True
                                yield out
                                continue
            yield l0
    
    return '\n'.join(walk())


def keep_indents_on_empty_lines(code: str) -> str:
    """
    before:             |   after:
        def foo():      |       def foo():
            pass        |           pass
                        |       ....            # <- modified
        def bar():      |       def bar():
            pass        |           pass
    """
    
    def walk() -> t.Iterator[str]:
        for curr, next in _continous_window(code.splitlines(), 2):
            if curr == '':
                if next and next.startswith(' '):
                    yield _keep_indent(curr, next)
                    continue
            yield curr
    
    return '\n'.join(walk())


def no_heavy_single_line(code: str) -> str:
    """
    before:
        foo(
            'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
            'y',
        )
    after:
        foo(
            'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
            'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
            'y',
        )
    
    before:
        foo(
            aaaaaaaaaaaaaaaaaa, bbbbbbbbbbbb, cccccc, dddddddd, eeeeeeeeeeeeeeee
        )
    after:
        foo(
            aaaaaaaaaaaaaaaaaa, bbbbbbbbbbbb,
            cccccc, dddddddd, eeeeeeeeeeeeeeee
        )
    """
    
    def walk() -> t.Iterator[str]:
        line: int
        prev: str
        curr: str
        next: str
        
        def is_heavy_line() -> bool:
            if prev.endswith('(') and next.lstrip().startswith(')'):
                if len(curr) > 70 and len(curr.strip()) > 40:
                    if len(prev.strip()) < 10 and len(next.strip()) < 10:
                        return True
            return False
        
        def is_triple_quotes() -> bool:
            # this is not a strict check, but it's enough for now.
            return (curr.lstrip().startswith(('"""', "'''")) or
                    curr.endswith(('"""', "'''")))  # fmt:skip
        
        is_processing = True
        
        for line, (prev, curr, next) in enumerate(
            _continous_window(code.splitlines(), 3, prepad=1)
        ):
            if curr.lstrip().startswith('#'):
                yield curr
                continue
            if is_triple_quotes():
                is_processing = not is_processing
                yield curr
                continue
            if not is_processing:
                yield curr
                continue
            
            if is_heavy_line():
                print(
                    ':i2sv',
                    'detected heavy line',
                    _re_leading_spaces.sub(
                        lambda m: m.group().replace(' ', '.'), curr
                    ),
                )
                try:
                    snippet = black.format_str(
                        'foo(\n    {}\n)'.format(curr.lstrip()),
                        mode=black.Mode(
                            line_length=50,
                            string_normalization=False,
                            magic_trailing_comma=True,
                            preview=True,
                        ),
                    )
                except Exception:
                    yield curr
                    continue
                snippet = snippet.splitlines()[1:-1]
                snippet = indent(
                    dedent('\n'.join(snippet)),
                    _re_leading_spaces.match(curr).group(),
                )
                yield snippet
            else:
                yield curr
    
    return '\n'.join(walk())


# -----------------------------------------------------------------------------


def _keep_indent(target: str, base: str) -> str:
    return _re_leading_spaces.match(base).group() + target


def _window(
    seq: t.List[str], n: int, prepad: int = 0
) -> t.Iterator[t.Tuple[str, ...]]:
    """
    for example:
        _window((1, 2, 3, 4, 5), 3)
            -> ((1, 2, 3), (4, 5, None))
    """
    assert 0 <= prepad < n <= len(seq), (len(seq), n, prepad)
    seq_fill = [None] * prepad + seq.copy() + [None] * n
    for i in range(0, len(seq_fill), n):
        win = seq_fill[i : i + n]
        if all(x is None for x in win): break
        yield (x or '' for x in win)
        if win[-1] is None: break


def _continous_window(
    seq: t.List[str], n: int, prepad: int = 0
) -> t.Iterator[t.Tuple[str, ...]]:
    """
    for example:
        _continous_window((1, 2, 3, 4, 5), 3)
            -> ((1, 2, 3), (2, 3, 4), (3, 4, 5))
    """
    assert 0 <= prepad < n <= len(seq), (len(seq), n, prepad)
    seq_fill = [None] * prepad + seq.copy() + [None] * n
    for i in range(0, len(seq_fill)):
        win = seq_fill[i : i + n]
        if all(x is None for x in win): break
        # at least one element is not None in `win`.
        yield (x or '' for x in win)
