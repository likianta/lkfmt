import os

import autoflake
import black
import isort
import lk_logger

lk_logger.setup(quiet=True, show_varnames=True)


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

    print('[green]reformat code done[/]', ':rt')
    return code
