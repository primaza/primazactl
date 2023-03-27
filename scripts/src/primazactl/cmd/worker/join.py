import os
import argparse
from pathlib import Path
from primazactl.errors import AtLeastOneError
from primazactl.types import \
    existing_file, kubernetes_name, semvertag_or_latest
from primazactl.primazamain.primazamain import PrimazaMain
from primazactl.utils.kubeconfig import from_env
from primazactl.primazaworker.primazaworker import PrimazaWorker


def add_join(parser: argparse.ArgumentParser, parents=[]):
    join_parser = parser.add_parser(
        name="join",
        help="Join Primaza",
        parents=parents)
    join_parser.set_defaults(func=join_primaza)
    add_args_join(join_parser)
    return join_parser


def add_args_join(parser: argparse.ArgumentParser):
    # primazactl
    parser.add_argument(
        "-f", "--config",
        dest="config",
        type=existing_file,
        required=False,
        help="primaza config file. Takes precedence over --version")

    parser.add_argument(
        "-v", "--version",
        dest="version",
        required=False,
        help="Version of primaza to use. Ignored if --config is set.",
        type=semvertag_or_latest)

    # worker
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

    # main
    parser.add_argument(
        "-d", "--clusterenvironment",
        dest="cluster_environment",
        type=kubernetes_name,
        required=True,
        help="name to use for the ClusterEnvironment that \
                will be created in Primaza")

    parser.add_argument(
        "-e", "--environment",
        dest="environment",
        type=kubernetes_name,
        required=True,
        help="the Environment that will be associated to \
                the ClusterEnvironment")

    parser.add_argument(
        "-l", "--primaza-kubeconfig",
        dest="main_kubeconfig",
        required=False,
        help=f"path to kubeconfig file, default: KUBECONFIG \
                   environment variable if set, otherwise \
                   {(os.path.join(Path.home(),'.kube','config'))}",
        type=existing_file,
        default=from_env())

    parser.add_argument(
        "-m", "--primaza-clustername",
        dest="main_clustername",
        required=False,
        help="name of cluster, as it appears in kubeconfig, \
                on which Primaza is installed. Default: \
                current kubeconfig context",
        type=str,
        default=None)


def join_primaza(args):
    validate(args)

    main = PrimazaMain(
        cluster_name=args.main_clustername,
        kubeconfig_path=args.main_kubeconfig,
        config_file=None,
        version=None,
    )

    PrimazaWorker(
        primaza_main=main,
        cluster_name=args.cluster_name,
        kubeconfig_file=args.kubeconfig,
        config_file=args.config,
        version=args.version,
        environment=args.environment,
        cluster_environment=args.cluster_environment,
    ).install_worker()

    print("Install and configure worker completed")


def validate(args):
    if not args.config and not args.version:
        raise AtLeastOneError("--config", "--version")
