import argparse
import sys
from primazactl.cmd.main.parser import add_group as main_add_group
from primazactl.cmd.worker.parser import add_group as worker_add_group


class PrimazactlParser(argparse.ArgumentParser):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        sys.exit(2)


def build_parser() -> argparse.ArgumentParser:
    parser = PrimazactlParser(
        prog='primazactl',
        description='Configure and install primaza and primaza '
                    'worker on clusters',
        epilog="Brought to you by the RedHat app-services team.")

    base_subparser = argparse.ArgumentParser(add_help=False)
    base_subparser.add_argument(
        "-x", "--verbose",
        dest="verbose",
        required=False,
        action="count",
        help="Set for verbose output")

    subparsers = parser.add_subparsers()
    main_add_group(subparsers, parents=[base_subparser])
    worker_add_group(subparsers, parents=[base_subparser])

    return parser
