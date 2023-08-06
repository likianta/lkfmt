import os
import typing as t

import autoflake
import isort
import lk_logger
from lk_utils import dumps
from lk_utils import fs
from lk_utils import loads
from lk_utils import xpath

from . import lkflavored as lkf
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
    if backdoor.pop('debug', False):
        _debug = True
        print(f'{backdoor = }', ':v')
    if backdoor.pop('direct_to_fmt_file', False):
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
        maxlen = max(map(len, map(fs.filename, files)))
        return min((maxlen, 80, lk_logger.console.console.width))
    
    file_col_width = estimate_best_column_width(files)
    cnt = 0
    for f in files:
        _, (i, u, d) = fmt_one(f, inplace, chdir, quiet=True, **backdoor)
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
    file: str,
    inplace: bool = True,
    chdir: bool = False,
    quiet: bool = False,
    formatter: t.Literal['autopep8', 'black', 'yapf'] = 'black',
) -> t.Tuple[str, T.Changes]:
    if quiet:
        lk_logger.mute()
    print(':v2s', file)
    assert file.endswith(('.py', '.txt'))
    if chdir:
        os.chdir(os.path.dirname(os.path.abspath(file)))
    
    with open(file, 'r', encoding='utf-8') as f:
        code = origin_code = f.read()
    
    # remove unused imports
    if not fs.filename(file) == '__init__.py':
        # we don't strip any import in `__init__.py`.
        code = autoflake.fix_code(
            code,
            remove_all_unused_imports=True,
            ignore_pass_statements=False,
            ignore_pass_after_docstring=False,
        )
    
    # sort imports
    code = isort.code(
        code,
        config=isort.Config(
            case_sensitive=True,
            force_single_line=True,
            line_length=80,
            only_modified=True,
            profile='black',
            reverse_relative=True,
        ),
    )
    
    # main format code
    if formatter == 'autopep8':
        import autopep8
        
        code = autopep8.fix_code(
            code,
            encoding='utf-8',
            options={
                'experimental': True,
                'max_line_length': 80,
            },
        )
    elif formatter == 'black':
        import black
        
        code = black.format_str(
            code,
            mode=black.Mode(
                line_length=80,
                string_normalization=False,
                magic_trailing_comma=True,
                preview=True,
            ),
        )
    elif formatter == 'yapf':
        import yapf
        
        code, _ = yapf.yapf_api.FormatCode(
            code,
            filename=fs.filename(file),
            # ref: yapf.yapflib.style._STYLE_HELP
            style_config={
                'ALIGN_CLOSING_BRACKET_WITH_VISUAL_INDENT': True,
                'ALLOW_MULTILINE_DICTIONARY_KEYS': True,
                'ALLOW_MULTILINE_LAMBDAS': True,
                'ALLOW_SPLIT_BEFORE_DEFAULT_OR_NAMED_ASSIGNS': True,
                'ALLOW_SPLIT_BEFORE_DICT_VALUE': True,
                'ARITHMETIC_PRECEDENCE_INDICATION': True,
                'BLANK_LINE_BEFORE_NESTED_CLASS_OR_DEF': True,
                'COALESCE_BRACKETS': True,
                'COLUMN_LIMIT': 80,
                'DEDENT_CLOSING_BRACKETS': True,
                'DISABLE_ENDING_COMMA_HEURISTIC': False,
                'EACH_DICT_ENTRY_ON_SEPARATE_LINE': True,
                'FORCE_MULTILINE_DICT': False,
                'INDENT_BLANK_LINES': True,
                'INDENT_CLOSING_BRACKETS': False,
                'INDENT_DICTIONARY_VALUE': True,
                'JOIN_MULTIPLE_LINES': True,
                'NO_SPACES_AROUND_SELECTED_BINARY_OPERATORS': True,
                'SPACE_BETWEEN_ENDING_COMMA_AND_CLOSING_BRACKET': False,
                'SPACES_BEFORE_COMMENT': 2,
                'SPLIT_ARGUMENTS_WHEN_COMMA_TERMINATED': True,
                'SPLIT_BEFORE_ARITHMETIC_OPERATOR': True,
                'SPLIT_BEFORE_BITWISE_OPERATOR': True,
                'SPLIT_BEFORE_CLOSING_BRACKET': False,
                'SPLIT_BEFORE_DICT_SET_GENERATOR': True,
                'SPLIT_BEFORE_DOT': True,
                'SPLIT_BEFORE_EXPRESSION_AFTER_OPENING_PAREN': True,
                'SPLIT_BEFORE_FIRST_ARGUMENT': True,
                'SPLIT_BEFORE_LOGICAL_OPERATOR': False,
                'SPLIT_COMPLEX_COMPREHENSION': True,
            },
        )
    else:
        raise Exception(formatter)
    
    code = lkf.join_oneline_if_stmt(code)
    code = lkf.no_heavy_single_line(code)
    code = lkf.keep_indents_on_empty_lines(code)
    code = lkf.ensure_trailing_newline(code)
    
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
