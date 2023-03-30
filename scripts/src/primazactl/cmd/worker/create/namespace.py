import argparse
import traceback
import sys
from primazactl.types import kubernetes_name
from primazactl.primazaworker.workernamespace import WorkerNamespace
from .constants import SERVICES, APPLICATIONS


def add_create_applications_namespace(parser: argparse.ArgumentParser,
                                      parents=[]):
    applications_namespace_parser = parser.add_parser(
        "applications-namespace",
        help="Create a namespace for applications",
        parents=parents)
    applications_namespace_parser.set_defaults(
        func=create_applications_namespace)
    add_args_namespace(applications_namespace_parser)


def add_create_services_namespace(parser: argparse.ArgumentParser,
                                  parents=[]):
    services_namespace_parser = parser.add_parser(
        "services-namespace",
        help="Create a namespace for services",
        parents=parents)
    services_namespace_parser.set_defaults(func=create_services_namespace)
    add_args_namespace(services_namespace_parser)


def add_args_namespace(parser: argparse.ArgumentParser):

    parser.add_argument(
        "-d", "--clusterenvironment",
        dest="cluster_environment",
        type=kubernetes_name,
        required=True,
        help="name to use for the ClusterEnvironment that \
                will be created in Primaza")

    parser.add_argument(
        "-c", "--clustername",
        dest="cluster_name",
        type=str,
        required=False,
        help="name of worker cluster, as it appears in kubeconfig, \
                  on which to create the namespace, default: \
                  current kubeconfig context",
        default=None)

    parser.add_argument(
        "-m", "--primaza-clustername",
        dest="main_clustername",
        required=False,
        help="name of cluster, as it appears in kubeconfig, \
                on which Primaza is installed. Default: \
                current kubeconfig context",
        type=str,
        default=None)


def create_applications_namespace(args):
    try:
        namespace = WorkerNamespace(APPLICATIONS,
                                    args.cluster_environment,
                                    args.cluster_name,
                                    args.main_clustername)
        namespace.create()
        print("Applications namespace was successfully created")
    except Exception:
        print(traceback.format_exc())
        print("\nAn exception creating an applications namespace",
              file=sys.stderr)


def create_services_namespace(args):
    try:
        namespace = WorkerNamespace(SERVICES,
                                    args.cluster_environment,
                                    args.cluster_name,
                                    args.main_clustername)
        namespace.create()
        print("Services namespace was successfully created.")
    except Exception as e:
        print(traceback.format_exc())
        print(f"\n\nAn exception occurred creating a services namespace: {e}",
              file=sys.stderr)
