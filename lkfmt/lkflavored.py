import re
import typing as t

re_spaces = re.compile(r'^ +')


def keep_indents_on_empty_lines(code: str) -> str:
    def walk() -> t.Iterator[str]:
        for curr, next in zip(code.splitlines(), code.splitlines()[1:] + ['']):
            if curr == '':
                if next and next.startswith(' '):
                    yield re_spaces.match(next).group() + curr
                    continue
            yield curr

    return '\n'.join(walk())


def ensure_trailing_newline(code: str) -> str:
    if not code.endswith('\n'):
        code += '\n'
    return code
