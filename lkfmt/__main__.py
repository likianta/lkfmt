from argsense import cli
from lk_utils import loads

from . import diff
from .formatter import fmt_all
from .formatter import fmt_one

cli.add_cmd(fmt_all, name='fmt')


@cli.cmd()
def show_diff(file: str) -> None:
    src_code = loads(file, 'plain')
    dst_code, _ = fmt_one(file, inplace=False, quiet=False)
    diff.show_diff(src_code, dst_code)
    diff.stat_changes(src_code, dst_code, verbose=True)


def _shortcut() -> None:
    """
    poetry build to be executable script.
    """
    cli.run(fmt_all)


if __name__ == '__main__':
    # pox -m lkfmt -h
    # pox -m lkfmt fmt $file
    # pox -m lkfmt show-diff $file
    cli.run()
