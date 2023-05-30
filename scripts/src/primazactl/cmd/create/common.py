import os
import argparse
from pathlib import Path
from primazactl.errors import AtLeastOneError
from primazactl.types import existing_file, semvertag_or_latest
from primazactl.utils.kubeconfig import from_env


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
        help="Version of primaza to use. Ignored if --config is set.",
        type=semvertag_or_latest)

    # main
    parser.add_argument(
        "-c", "--context",
        dest="context",
        type=str,
        required=False,
        help="name of cluster, as it appears in kubeconfig, \
                  on which to install primaza or worker, default: \
                  current kubeconfig context",
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


def validate(args):
    if not args.config and not args.version:
        raise AtLeastOneError("--config", "--version")
