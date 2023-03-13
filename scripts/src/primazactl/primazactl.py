import argparse
import os
import re
import semver
import traceback
from pathlib import Path
from primazactl.primazamain import primazamain
from primazactl.primazaworker import primazaworker
from primazactl.utils import logger

PRIMAZA_MAIN = "main"
PRIMAZA_WORKER = "worker"


def kubernetes_name(name_input):
    pattern = re.compile("^(([a-z0-9]|[a-z0-9][a-z0-9-]*[a-z0-9]).)*"
                         "([a-z0-9]|[a-z0-9][a-z0-9-]*[a-z0-9])$")
    if not pattern.match(name_input):
        print("\n[ERROR] value must consist of lower case alphanumeric "
              "characters, \'-\' or \'.\', and must start and end with "
              "an alphanumeric character\n")
        raise ValueError
    return name_input


def main():

    parser = argparse.ArgumentParser(
        prog='primazactl',
        description=f'Configure and install primaza {PRIMAZA_MAIN} and '
                    f'{PRIMAZA_WORKER} on clusters')

    parser.add_argument("action", type=str,
                        choices=["install", "info", "uninstall", "join"],
                        help='type of action to perform.')
    parser.add_argument('install_type', type=str,
                        choices=[PRIMAZA_MAIN, PRIMAZA_WORKER],
                        help=f'specify {PRIMAZA_MAIN} or {PRIMAZA_WORKER}.')
    parser.add_argument("-c", "--clustername",
                        dest="cluster_name", type=kubernetes_name,
                        required=False,
                        help=f"name of cluster, as it appears in kubeconfig, "
                             f"on which to install {PRIMAZA_MAIN} or "
                             f"{PRIMAZA_WORKER}, default: current "
                             f"kubeconfig context")
    parser.add_argument("-d", "--clusterevironmentname",
                        dest="cluster_environment_name", type=kubernetes_name,
                        required=False,
                        help="name to use for the ClusterEnvironment that "
                             "will be created in Primaza. Required for "
                             f"{PRIMAZA_WORKER} install.")
    parser.add_argument("-e", "--environment",
                        dest="environment", type=kubernetes_name,
                        required=False,
                        help="the Environment that will be associated to "
                             "the ClusterEnvironment. Required for "
                             f"{PRIMAZA_WORKER} install.")
    parser.add_argument("-f", "--config",
                        dest="primaza_config", type=argparse.FileType('r'),
                        required=False,
                        help=f"primaza {PRIMAZA_MAIN} or {PRIMAZA_WORKER}"
                             f" config file. Takes precedence over --version")
    parser.add_argument("-k", "--kubeconfig",
                        dest="kubeconfig", type=argparse.FileType('r'),
                        required=False,
                        help=f"path to kubeconfig file, default: KUBECONFIG \
                               environment variable if set, otherwise \
                               {os.path.join(Path.home(),'.kube','config')}")
    parser.add_argument("-l", f"--{PRIMAZA_MAIN}kubeconfig",
                        dest="main_kubeconfig", type=argparse.FileType('r'),
                        required=False,
                        help=f"path to kubeconfig file for {PRIMAZA_MAIN}, "
                             f"default: --kubeconfig if set, KUBECONFIG "
                             f"environment variable if set, otherwise "
                             f"{os.path.join(Path.home(),'.kube','config')}."
                             f" Used for {PRIMAZA_WORKER} install.")
    parser.add_argument("-m", f"--{PRIMAZA_MAIN}clustername",
                        dest="main_cluster_name", type=kubernetes_name,
                        required=False,
                        help=f"name of cluster, as it appears in kubeconfig,"
                             f" on which {PRIMAZA_MAIN} is installed. "
                             f"Defaults to {PRIMAZA_WORKER} install cluster.")
    parser.add_argument("-p", "--privatekey",
                        dest="private_key", type=argparse.FileType('r'),
                        required=False,
                        help=f"primaza {PRIMAZA_MAIN} private key file. "
                             f"Required for {PRIMAZA_WORKER} install")
    parser.add_argument("-n", "--namespace",
                        dest="namespace", type=kubernetes_name,
                        required=False,
                        help="namespace to use for install. Default: "
                             "primaza_system")
    parser.add_argument("-v", "--version",
                        dest="primaza_version", type=str, required=False,
                        help=f"Version of primaza {PRIMAZA_MAIN} or "
                             f"{PRIMAZA_WORKER} to use, default: newest "
                             "release available. Ignored if --config "
                             "is set.")
    parser.add_argument("-x", "--verbose", required=False,
                        action=argparse.BooleanOptionalAction,
                        help="Set for verbose output")

    args = parser.parse_args()

    if args.verbose:
        logger.set_verbose(True)

    cluster_name = args.cluster_name
    main_cluster_name = args.main_cluster_name
    if not main_cluster_name:
        main_cluster_name = cluster_name

    if not args.kubeconfig:
        kube_config = os.environ.get("KUBECONFIG")
        if not kube_config:
            kube_config = str(os.path.join(Path.home(), ".kube", "config"))
    else:
        kube_config = args.kubeconfig.name

    main_kubeconfig = kube_config
    if args.main_kubeconfig:
        main_kubeconfig = args.main_kubeconfig.name

    private_key = None
    if args.private_key:
        private_key = args.private_key.name

    primaza_config = None
    if args.primaza_config:
        primaza_config = args.primaza_config.name
        primaza_version = None
    else:
        primaza_version = args.primaza_version
        if primaza_version:
            if not semver.VersionInfo.isvalid(primaza_version):

                parser.error("\n[ERROR] --version is not a valid semantic "
                             f"version: {primaza_version}\n")

    if args.action == "install":

        if args.install_type == PRIMAZA_WORKER:
            if not private_key \
                    or not args.environment \
                    or not args.cluster_environment_name:
                parser.error("[ERROR] --privatekey, --environment and "
                             "--cluster-environment are "
                             f"required for {PRIMAZA_WORKER} install")
            logger.log_info(f"Install and configure {PRIMAZA_MAIN} "
                            "is in progress")
            try:

                primaza_main = primazamain.PrimazaMain(main_cluster_name,
                                                       main_kubeconfig,
                                                       None, None,
                                                       private_key,
                                                       args.namespace)

                worker = primazaworker.\
                    PrimazaWorker(primaza_main,
                                  cluster_name,
                                  kube_config,
                                  primaza_config,
                                  primaza_version,
                                  args.environment,
                                  args.cluster_environment_name,
                                  args.namespace)

                worker.install_worker()
                logger.log_info(f"Install and configure {PRIMAZA_WORKER} "
                                f"completed", True)
            except Exception as err:
                if args.verbose:
                    traceback.print_exc()
                if cluster_name:
                    parser.error(f"[ERROR] installing primaza "
                                 f"{PRIMAZA_WORKER} on {cluster_name}: {err}")
                else:
                    parser.error(f"[ERROR] installing primaza "
                                 f"{PRIMAZA_WORKER}: {err}")

        else:
            logger.log_info(f"Install and configure {PRIMAZA_MAIN} "
                            f"is in progress")
            try:
                primaza_main = primazamain.PrimazaMain(cluster_name,
                                                       kube_config,
                                                       primaza_config,
                                                       primaza_version,
                                                       private_key,
                                                       args.namespace)
                primaza_main.install_primaza()
                logger.log_info(f"Install and configure {PRIMAZA_MAIN} "
                                f"completed", True)
            except Exception as err:
                if args.verbose:
                    traceback.print_exc()
                if cluster_name:
                    parser.error(f"[ERROR] installing primaza "
                                 f"{PRIMAZA_MAIN} on {cluster_name}: {err}")
                else:
                    parser.error(f"[ERROR] installing primaza "
                                 f"{PRIMAZA_MAIN}: {err}")
    else:
        parser.error("info, uninstall and join are not yet implemented.")


if __name__ == "__main__":
    main()
