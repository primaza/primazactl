import argparse
import sys
from primazactl.cmd.create.parser import add_group as create_add_group
from primazactl.cmd.join.parser import add_group as join_add_group
from primazactl.cmd.apply.parser import add_group as apply_add_group
from primazactl.version import __version__


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
        epilog=f"You are running primazactl version {__version__},"
               f" brought to you by the RedHat app-services team.")

    base_subparser = argparse.ArgumentParser(add_help=False)

    base_subparser.add_argument(
        "-x", "--verbose",
        dest="verbose",
        required=False,
        action="count",
        help="Set for verbose output")

    subparsers = parser.add_subparsers()
    create_add_group(subparsers, parents=[base_subparser])

    # Remove delete for now - it does not work after cluster
    # join because the tenant namespace will not delete as
    # it contains the ClusterEnvironment.
    # delete_add_group(subparsers, parents=[base_subparser])

    join_add_group(subparsers, parents=[base_subparser])
    apply_add_group(subparsers, parents=[base_subparser])

    return parser
