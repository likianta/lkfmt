import os
import typing as t
from difflib import ndiff

import autoflake
import black
import isort
import lk_logger

lk_logger.setup(quiet=True, show_funcname=False, show_varnames=True)


def fmt(file: str, inplace: bool = True, chdir: bool = False) -> str:
    """
    kwargs:
        inplace (-i):
        chdir (-c):
    """
    print(':v2s', file)
    assert file.endswith(('.py', '.txt'))
    if chdir:
        os.chdir(os.path.dirname(os.path.abspath(file)))

    with open(file, 'r', encoding='utf-8') as f:
        code = origin_code = f.read()

    code = black.format_str(
        code,
        mode=black.Mode(
            line_length=80,
            string_normalization=False,
            magic_trailing_comma=False,
            preview=True,
        ),
    )
    code = isort.code(
        code,
        config=isort.Config(
            case_sensitive=True,
            force_single_line=True,
            line_length=80,
            only_modified=True,
            profile='black',
        ),
    )
    code = autoflake.fix_code(
        code,
        remove_all_unused_imports=True,
        ignore_pass_statements=False,
        ignore_pass_after_docstring=False,
    )

    if code == origin_code:
        print('[green dim]no code change[/]', ':rt')
        return code

    if inplace:
        with open(file, 'w', encoding='utf-8') as f:
            f.write(code)

    i, u, d = _stat(origin_code, code)
    print(
        '[green]reformat code done: '
        '[cyan {dim_i}][u]{i}[/] insertions,[/] '
        '[yellow {dim_u}][u]{u}[/] updates,[/] '
        '[red {dim_d}][u]{d}[/] deletions[/]'
        '[/]'.format(
            dim_i='dim' if not i else '',
            dim_u='dim' if not u else '',
            dim_d='dim' if not d else '',
            i=i,
            u=u,
            d=d,
        ),
        ':rt',
    )
    return code


def _stat(old: str, new: str) -> t.Tuple[int, int, int]:
    """
    returns:
        tuple[insertions, updates, deletions]
    """
    insertions = updates = deletions = 0
    for d in ndiff(old.splitlines(), new.splitlines(keepends=False)):
        if d.startswith('+'):
            insertions += 1
        elif d.startswith('-'):
            deletions += 1
        elif d.startswith('?'):
            updates += 1
    return insertions, updates, deletions
