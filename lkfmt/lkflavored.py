import re
import string
import typing as t

_re_spaces = re.compile(r'^ +')


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
        prev: str
        curr: str
        next: str
        
        def is_heavy_quoted_line() -> bool:
            if prev.endswith('(') and next.lstrip().startswith(')'):
                if len(curr) > 70:
                    if curr.strip().startswith(('"', "'")) and curr.endswith(
                        ('",', "',", '"', "'")
                    ):
                        if len(prev.strip()) < 10 or len(next.strip()) < 40:
                            return True
            return False
        
        def is_heavy_line() -> bool:
            if prev.endswith('(') and next.strip().startswith(')'):
                if len(curr) > 70:
                    if len(prev) < 40 and len(next) < 10:
                        return True
            return False
        
        def find_proper_split_point(
            text: str, limit_steps: int
        ) -> t.Optional[int]:
            # find a better split point, for example a \
            # whitespace.
            i: int
            for i, (a, b) in enumerate(_continous_window([x for x in text], 2)):
                if a == ' ':
                    return i + 1
                if a in string.punctuation:
                    if b == ' ':
                        return i + 2
                    else:
                        return i + 1
                if i > limit_steps:
                    return None
            return None
        
        is_analysing = True
        
        for prev, curr, next in _continous_window(
            code.splitlines(), 3, prepad=1
        ):
            # print(':vi2', curr)
            if is_analysing and curr.endswith(('"""', "'''")):
                is_analysing = False
                yield curr
                continue
            if not is_analysing:
                if curr.startswith(('"""', "'''")):
                    is_analysing = True
                yield curr
                continue
            
            if (is_quoted := is_heavy_quoted_line()) or is_heavy_line():
                print('detected heavy line', curr, ':vi2')
                mid = len(curr) // 2
                if i := find_proper_split_point(curr[mid:], 10):
                    split_point = mid + i
                # find in reverse direction.
                elif j := find_proper_split_point(curr[mid - 10 :], 10):
                    split_point = mid - (10 - j)
                else:
                    if is_quoted:
                        # remain using the original split point.
                        split_point = mid
                    else:
                        yield curr
                        continue
                if is_quoted:
                    quote = curr.lstrip()[0]
                    yield curr[:split_point] + quote
                    yield _keep_indent(quote + curr[split_point:], curr)
                else:
                    yield curr[:split_point]
                    yield _keep_indent(curr[split_point:], curr)
            else:
                yield curr
    
    return '\n'.join(walk())


# -----------------------------------------------------------------------------


def _keep_indent(target: str, base: str) -> str:
    if base.startswith(' '):
        return _re_spaces.match(base).group() + target
    return target


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
