import os
import argparse
from pathlib import Path
from primazactl.errors import AtLeastOneError
from primazactl.types import \
    existing_file, kubernetes_name, semvertag_or_latest
from primazactl.utils.kubeconfig import from_env
from primazactl.primazamain.constants import DEFAULT_TENANT


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
        "-c", "--clustername",
        dest="cluster_name",
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

    parser.add_argument(
        "-t", "--tenant",
        dest="tenant",
        type=kubernetes_name,
        required=False,
        help=f"tenant to create. Default: \
            {DEFAULT_TENANT}",
        default=DEFAULT_TENANT)


def validate(args):
    if not args.config and not args.version:
        raise AtLeastOneError("--config", "--version")
