import argparse
import traceback
import sys
import os
from pathlib import Path
from primazactl.types import kubernetes_name, \
    existing_file, \
    semvertag_or_latest
from primazactl.primazamain.constants import DEFAULT_TENANT
from primazactl.version import __primaza_version__
from .constants import SERVICE, APPLICATION
from primazactl.utils import settings
from primazactl.utils import logger
from primazactl.cmd.options.options import Options


def add_args_namespace(parser: argparse.ArgumentParser, type):
    parser.add_argument(
        "namespace",
        type=kubernetes_name,
        help="namespace to create")

    parser.add_argument(
        "-d", "--cluster-environment",
        dest="cluster_environment",
        type=kubernetes_name,
        required=True,
        help="name to use for the ClusterEnvironment that \
                will be created in Primaza")

    parser.add_argument(
        "-c", "--context",
        dest="context",
        type=str,
        required=False,
        help="name of cluster, as it appears in kubeconfig, "
             "on which to create the service or application namespace, "
             "default: current kubeconfig context",
        default=None)

    parser.add_argument(
        "-m", "--tenant-context",
        dest="tenant_context",
        required=False,
        help="name of cluster, as it appears in kubeconfig, \
                on which Primaza tenant was created. Default: \
                current kubeconfig context",
        type=str,
        default=None)

    parser.add_argument(
        "-f", "--config",
        dest="config",
        type=existing_file,
        required=False,
        help="Config file containing agent roles")

    parser.add_argument(
        "-t", "--tenant",
        dest="tenant",
        type=kubernetes_name,
        required=False,
        help=f"tenant to use. Default: {DEFAULT_TENANT}",
        default=None)

    parser.add_argument(
        "-u", "--tenant-internal-url",
        dest="tenant_internal_url",
        type=str,
        required=False,
        help="Internal URL for the cluster \
                on which Primaza's Control Plane is running",
        default=None)

    parser.add_argument(
        "-v", "--version",
        dest="version",
        required=False,
        help=f"Version of primaza to use, default: {__primaza_version__}. "
             "Ignored if --config is set.",
        type=semvertag_or_latest,
        default=None)

    parser.add_argument(
        "-k", "--kubeconfig",
        dest="kubeconfig",
        required=False,
        help=f"path to kubeconfig file, default: KUBECONFIG \
                   environment variable if set, otherwise \
                   {(os.path.join(Path.home(),'.kube','config'))}",
        type=existing_file,
        default=None)

    parser.add_argument(
        "-l", "--tenant-kubeconfig",
        dest="tenant_kubeconfig",
        required=False,
        help=f"path to kubeconfig file for the tenant, default: KUBECONFIG \
                   environment variable if set, otherwise \
                   {(os.path.join(Path.home(),'.kube','config'))}",
        type=existing_file,
        default=None)

    parser.add_argument("-p", "--options",
                        dest="options_file",
                        type=existing_file,
                        required=False,
                        help="primaza options file in which default "
                             "command line options are specified. Options "
                             "set on the command line take precedence.")

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


def __create_namespace(args, type):
    try:
        settings.set(args)

        options = Options(args)
        tenant = options.get_tenant()
        error = tenant.create_only(args.tenant_context,
                                   args.tenant,
                                   args.tenant_kubeconfig,
                                   args.tenant_internal_url)
        if error:
            logger.log_error(error)
            return

        cluster_environment = options.get_cluster_environment(
            args.cluster_environment, tenant)

        error = cluster_environment.create_only(args.cluster_environment,
                                                args.context,
                                                args.kubeconfig)

        if error:
            logger.log_error(error)
            return

        main_user = tenant.main.create_primaza_identity(
            cluster_environment.name)
        kcfg = tenant.main.get_kubeconfig(main_user)

        agent = cluster_environment.get_agent(args.namespace, type)
        error = agent.create(args.config, args.version)
        if error:
            logger.log_info(f"Create of {agent.type} namespace "
                            f"{agent.name} failed: {error}")
            return

        cluster_environment.worker.create_namespaced_kubeconfig_secret(
            kcfg, tenant.tenant)

        if settings.output_active():
            settings.output()
        elif settings.dry_run_active():
            print(f"Dry run create {type} namespace "
                  f"{args.namespace} successfully completed.")
        else:
            agent.agent.check()
            print(f"Create {type} namespace {args.namespace} "
                  f"successfully completed")

    except Exception as e:
        if args.verbose:
            print(traceback.format_exc())
        print(f"\nAn exception creating an {type} namespace",
              file=sys.stderr)
        raise e


def create_application_namespace(args):
    __create_namespace(args, APPLICATION)


def create_service_namespace(args):
    __create_namespace(args, SERVICE)
