import re
import typing as t
from textwrap import dedent
from textwrap import indent

import black

_re_leading_spaces = re.compile(r'^ *')


def ensure_trailing_newline(code: str) -> str:
    if not code.endswith('\n'):
        code += '\n'
    return code


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
                snippet = black.format_str(
                    'foo(\n    {}\n)'.format(curr.lstrip()),
                    mode=black.Mode(
                        line_length=50,
                        string_normalization=False,
                        magic_trailing_comma=True,
                        preview=True,
                    ),
                )
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
        if all(x is None for x in win):
            break
        yield (x or '' for x in win)
        if win[-1] is None:
            break


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
        if all(x is None for x in win):
            break
        # at least one element is not None in `win`.
        yield (x or '' for x in win)
