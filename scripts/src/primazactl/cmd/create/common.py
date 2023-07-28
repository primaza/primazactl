import os
import argparse
from pathlib import Path
from primazactl.types import existing_file, semvertag_or_latest
from primazactl.utils.kubeconfig import from_env
from primazactl.version import __primaza_version__
from primazactl.utils import settings


def add_shared_args(parser: argparse.ArgumentParser):
    # primazactl
    parser.add_argument(
        "-f", "--config",
        dest="config",
        required=False,
        help="primaza config file. Takes precedence over --version",
        type=existing_file)

    parser.add_argument(
        "-v", "--version",
        dest="version",
        required=False,
        help=f"Version of primaza to use, default: {__primaza_version__}. "
             "Ignored if --config is set.",
        type=semvertag_or_latest,
        default=__primaza_version__)

    parser.add_argument("-p", "--options",
                        dest="options_file",
                        type=existing_file,
                        required=False,
                        help="primaza options file in which default "
                             "command line options are specified. Options "
                             "set on the command line take precedence.")

    # main
    parser.add_argument(
        "-c", "--context",
        dest="context",
        type=str,
        required=False,
        help="name of cluster, as it appears in kubeconfig, on which to "
             "create the tenant, default: current kubeconfig context",
        default=None)

    parser.add_argument(
        "-k", "--kubeconfig",
        dest="kubeconfig",
        required=False,
        help=f"path to kubeconfig file, default: KUBECONFIG \
                   environment variable if set, otherwise \
                   {(os.path.join(Path.home(),'.kube','config'))}",
        type=existing_file,
        default=from_env())

    # options
    parser.add_argument(
        "-y", "--dry-run",
        dest="dry_run",
        type=str,
        required=False,
        choices=settings.DRY_RUN_CHOICES,
        default=settings.DRY_RUN_NONE,
        help=f"Set for dry run (default: {settings.DRY_RUN_NONE})")

    parser.add_argument(
        "-o", "--output",
        dest="output_type",
        type=str,
        required=False,
        choices=settings.OUTPUT_CHOICES,
        default=settings.OUTPUT_NONE,
        help="Set to get output of resources which are created "
             f"(default: {settings.OUTPUT_NONE}).")
