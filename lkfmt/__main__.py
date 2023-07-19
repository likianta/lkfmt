from argsense import cli

from .main import fmt

cli.add_cmd(fmt)


def _shortcut() -> None:
    """
    poetry build to be executable script.
    """
    cli.run(fmt)


if __name__ == '__main__':
    # pox -m lkfmt -h
    # pox -m lkfmt $file
    cli.run(fmt)
