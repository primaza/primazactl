import argparse
import sys
from primazactl.cmd.create.parser import add_group as create_add_group
from primazactl.cmd.delete.parser import add_group as delete_add_group
from primazactl.cmd.join.parser import add_group as join_add_group
from primazactl.version import __version__
from primazactl.utils import settings


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
    base_subparser.add_argument(
        "-y", "--dry-run",
        dest="dry_run",
        type=str,
        required=False,
        choices=settings.DRY_RUN_CHOICES,
        default=settings.DRY_RUN_NONE,
        help=f"Set for dry run (default: {settings.DRY_RUN_NONE})")
    base_subparser.add_argument(
        "-o", "--output",
        dest="output_type",
        type=str,
        required=False,
        choices=settings.OUTPUT_CHOICES,
        default=settings.OUTPUT_NONE,
        help="Set to get output of resources which are created "
             f"(default: {settings.OUTPUT_NONE}).")

    subparsers = parser.add_subparsers()
    create_add_group(subparsers, parents=[base_subparser])
    delete_add_group(subparsers, parents=[base_subparser])
    join_add_group(subparsers, parents=[base_subparser])

    return parser
