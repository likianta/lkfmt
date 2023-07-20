import re
import typing as t
from difflib import ndiff


class T:
    ChangeMark = t.Literal['+', '-', '?', ' ']
    Changes = t.Tuple[int, int, int]
    RawLine = str
    Diffs0 = t.List[t.Tuple[ChangeMark, t.Union[RawLine, t.Literal['+', '-']]]]
    Diffs1 = t.Iterator[
        t.Tuple[ChangeMark, t.Union[RawLine, t.Literal['+', '-']]]
    ]


def stat_changes(a: str, b: str, verbose=False) -> T.Changes:
    insertions = updates = deletions = 0
    for mark, _ in _squirsh_diffs(_diff(a.splitlines(), b.splitlines())):
        if mark == '+':
            insertions += 1
        elif mark == '-':
            deletions += 1
        elif mark == '?':
            updates += 1
    if verbose:
        print(
            '[cyan {dim_i}][u]{i}[/] insertions,[/] '
            '[yellow {dim_u}][u]{u}[/] updates,[/] '
            '[red {dim_d}][u]{d}[/] deletions[/]'.format(
                dim_i='dim' if not insertions else '',
                dim_u='dim' if not updates else '',
                dim_d='dim' if not deletions else '',
                i=insertions,
                u=updates,
                d=deletions,
            ),
            ':r',
        )
    return insertions, updates, deletions


def show_diff(a: str, b: str) -> None:
    print(':dfs', 'showing diff...')
    re_mask = re.compile(r'\^+')

    for index, (mark, line) in enumerate(
        _squirsh_diffs(_diff(a.splitlines(), b.splitlines()))
    ):
        print(
            ':rs1',
            '[{color}]'
            '[dim]\\[{index}]\\[{mark}] [bright_black]|[/] [/]'
            '{line}[/]'.format(
                color=(
                    'green'
                    if mark == '+'
                    else (
                        'red'
                        if mark == '-'
                        else 'yellow' if mark == '?' else 'default'
                    )
                ),
                index=str(index + 1).rjust(3),
                mark=mark,
                line=(
                    line.replace('[', '\\[')
                    if mark != '?'
                    else re_mask.sub(
                        lambda m: '[bright_black dim]{}[/]'.format(
                            m.group().replace('^', '.')
                        ),
                        line.replace('[', '\\['),
                    )
                ),
            ),
        )


def _diff(a: t.Sequence[str], b: t.Sequence[str]) -> T.Diffs0:
    from .formatter import _debug
    out: T.Diffs0 = []
    for diff in ndiff(a, b):
        mask, line = diff[0], diff[2:].replace('\n', '')
        if _debug:
            print(f'[{mask}]', line, ':vsi2')
        out.append((mask, line))  # noqa
    return out


# _re_only_ins = re.compile(r'\s*\++\s*')
# _re_only_del = re.compile(r'\s*-\s*')


def _squirsh_diffs(diffs: T.Diffs0) -> T.Diffs1:
    """
    note: the output length <= input's.
    """
    diffs += [(' ', None)] * 4

    def main() -> T.Diffs1:
        index = -1
        while True:
            index += 1

            a0, a1 = diffs[index]
            if a1 is None:
                break
            if a0 == '?':
                continue
            if a0 == ' ':
                yield a0, a1
                continue
            # assert a0 in ('+', '-')

            b0, b1 = diffs[index + 1]
            if b0 == '?':
                c0, c1 = diffs[index + 2]
                d0, d1 = diffs[index + 3]
                assert c0 != '?'

                if d0 == '?':
                    a2 = _mask(a1, b1)
                    c2 = _mask(c1, d1)
                    if a2 == c2:
                        # [a][-] xxx yyy z
                        # [b][?] ^^^^   --
                        # [c][+]     yyy
                        # [d][?] ^^^^                   (`c` has spaces changed)
                        a3 = _transform_3(a1, b1)
                        # c3 = _transform_3(c1, d1)
                        yield '?', a3
                        index += 2
                        continue
                else:
                    a2 = _transform_3(a1, b1)
                    if a2 == c1:
                        # [a][-] xxx yyy z
                        # [b][?] ^^^^   --
                        # [c][+]     yyy
                        yield '?', a2
                        index += 2
                    else:
                        yield '?', a2
                        index += 1
                    continue
            else:
                if a0 == '-' and b0 == '+':
                    if a1.strip() == b1.strip() == '':
                        # [a][-] ....                              (four spaces)
                        # [b][+]                                    (zero space)
                        yield '?', a1
                        index += 1
                        continue
                    c0, c1 = diffs[index + 2]
                    if c0 == '?':
                        # [a][-] )
                        # [b][+] ),           (`b` has an extra trailling comma)
                        # [c][?]  +
                        b2 = _mask(b1, c1)
                        if a1 == b2:
                            yield '?', b1
                            index += 2
                            continue
            yield a0, a1

    def _mask(text: str, mask: str) -> str:
        assert len(text) >= len(mask)
        out = ''
        for x, y in zip(text, mask.ljust(len(text))):
            if y == ' ':
                out += x
        return out

    def _transform_3(text: str, mask: str) -> str:
        assert len(text) >= len(mask)
        out = ''
        for x, y in zip(text, mask.ljust(len(text))):
            if y == ' ' or y == '+':
                out += x
            elif y == '^':
                out += '^'
        return out

    yield from main()
