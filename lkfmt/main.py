import os
import typing as t

import autoflake
import black
import isort
import lk_logger
from lk_utils import dumps
from lk_utils import fs
from lk_utils import loads
from lk_utils import xpath

from .diff import T
from .diff import stat_changes

lk_logger.setup(quiet=True, show_funcname=False, show_varnames=False)


class Cache:
    _cache: dict  # dict[path, mtime]
    _file: str
    
    def __init__(self):
        self._file = xpath('.cache.pkl')
        if os.path.exists(self._file):
            self._cache = loads(self._file)
        else:
            self._cache = {}
    
    def get(self, path: str) -> t.Union[float, 0]:
        return self._cache.get(path, 0)
    
    def set(self, path: str, mtime: float) -> None:
        self._cache[path] = mtime
    
    def save(self) -> None:
        dumps(self._cache, self._file)
    
    def disable(self) -> None:
        self._cache.clear()
        setattr(self, 'save', lambda: None)


_cache = Cache()
_debug = False


def fmt_all(
    target: str = '.',
    recursive: bool = False,
    inplace: bool = True,
    chdir: bool = False,
    no_cache: bool = False,
    **backdoor,
) -> None:
    """
    reformat one or many python files in likianta flavored style.

    kwargs:
        recursive (-r):
        inplace (-i):
        chdir (-c):
    backdoor: for third-party tool to quick access.
        debug: bool[False]. print more info in process.
        direct_to_fmt_file: bool[False]. directly call `fmt_file`.
        show_diff: bool[False]. show diff after reformat. (not implemented)
            [red]careful using this option, it may dump too much info -
            overwhelming your terminal.[/]
    """
    global _debug
    if backdoor.get('debug'):
        _debug = True
        print(f'{backdoor = }', ':v')
    if backdoor.get('direct_to_fmt_file'):
        fmt_one(target, inplace, chdir)
        return
    
    root: str
    files: t.List[str]
    
    if target == '.':
        root = fs.abspath(os.getcwd())
    elif os.path.isdir(target):
        root = fs.abspath(target)
    elif os.path.isfile(target):
        _cache.set(target, os.path.getmtime(target))
        fmt_one(target, inplace, chdir)
        return
    else:
        raise ValueError(f'invalid target: {target}')
    
    if no_cache:
        _cache.disable()
    if recursive:
        files = fs.findall_file_paths(root, '.py')
    else:
        files = fs.find_file_paths(root, '.py')
    if not files:
        print('[yellow dim]no python file found[/]', ':rt')
        return
    # filter
    temp = []
    for f in files:
        if (m := os.path.getmtime(f)) > _cache.get(f):
            temp.append(f)
            _cache.set(f, m)
    if temp:
        files = temp
        if _debug:
            print(files, ':vl')
    else:
        print('[green dim]no file modified[/]', ':rt')
        return
        
    def estimate_best_column_width(files: t.List[str]) -> int:
        max_width = max(map(len, map(fs.filename, files)))
        return min((max_width, lk_logger.console.console.width))
    
    file_col_width = estimate_best_column_width(files)
    cnt = 0
    for f in files:
        _, (i, u, d) = fmt_one(f, inplace, chdir, quiet=True)
        if (i, u, d) != (0, 0, 0):
            cnt += 1
        print(
            ':ir',
            '[green]reformat done: {} ({})[/]'.format(
                fs.relpath(f, root).ljust(file_col_width),
                (
                    '[green dim]no code change[/]'
                    if (i, u, d) == (0, 0, 0)
                    else (
                        '[cyan {dim_i}]{i} insertions,[/] '
                        '[yellow {dim_u}]{u} updates,[/] '
                        '[red {dim_d}]{d} deletions[/]'.format(
                            dim_i='dim' if not i else '',
                            dim_u='dim' if not u else '',
                            dim_d='dim' if not d else '',
                            i=str(i).rjust(2),
                            u=str(u).rjust(2),
                            d=str(d).rjust(2),
                        )
                    )
                ),
            ),
        )
    if cnt == 0:
        print(':rt', '[green dim]all done with no file changed[/]')
    else:
        print(':rt', f'[green]all done with [u]{cnt}[/] files changed[/]')
    _cache.save()


def fmt_one(
    file: str, inplace: bool = True, chdir: bool = False, quiet: bool = False
) -> t.Tuple[str, T.Changes]:
    if quiet:
        lk_logger.mute()
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
        return code, (0, 0, 0)
    
    if inplace:
        with open(file, 'w', encoding='utf-8') as f:
            f.write(code)
    
    i, u, d = stat_changes(origin_code, code, verbose=False)
    print(
        '[green]reformat code done: '
        '[cyan {dim_i}]{i} insertions,[/] '
        '[yellow {dim_u}]{u} updates,[/] '
        '[red {dim_d}]{d} deletions[/]'
        '[/]'.format(
            dim_i='dim' if not i else '',
            dim_u='dim' if not u else '',
            dim_d='dim' if not d else '',
            i=str(i).rjust(2),
            u=str(u).rjust(2),
            d=str(d).rjust(2),
        ),
        ':rt',
    )
    if quiet:
        lk_logger.unmute()
    return code, (i, u, d)
