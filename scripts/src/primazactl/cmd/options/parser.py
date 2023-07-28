import argparse
import traceback
from primazactl.types import existing_file
from primazactl.utils import settings
from primazactl.utils import logger
from primazactl.cmd.create.namespace.constants import APPLICATION, SERVICE
from .options import Options


def add_group(subparsers, parents=[]):
    run_options_parser = subparsers.add_parser(
        name="options",
        help="Run from an options file",
        parents=parents)
    run_options_parser.set_defaults(func=run_options)
    add_args_options(run_options_parser)
    return run_options_parser


def add_args_options(parser: argparse.ArgumentParser):
    parser.add_argument(
        "-p", "--options",
        dest="options_file",
        type=existing_file,
        required=True,
        help="primaza options file in which command line options are "
             "specified. All options in the file will be processed.")

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


def run_options(args):

    try:
        settings.set(args)

        options = Options(args)
        tenant = options.get_tenant()

        error = tenant.install(None, None, None, None, None)
        if error:
            logger.log_error(f"Primaza tenant {tenant.tenant} "
                             f"install failed: {error}")
            return

        error = tenant.main.check()
        if error:
            logger.log_error(f"Primaza tenant {tenant.tenant} "
                             f"failed to start: {error}")
            return

        if not settings.output_active():
            if settings.dry_run_active():
                print("Dry run create primaza tenant "
                      f"{tenant.tenant} "
                      "successfully completed\n")
            else:
                print(f"Create primaza tenant {tenant.tenant} "
                      f"successfully completed")

        for cluster_environment in options.get_cluster_environments(tenant):

            error = cluster_environment.join(None, None, None,
                                             None, None, None, None)
            if error:
                logger.log_error(error)
                return

            if not settings.output_active():
                if settings.dry_run_active():
                    print("Dry run join cluster "
                          f"{cluster_environment.name} "
                          "successfully completed.\n")
                else:
                    print(f"Join cluster {cluster_environment.name} "
                          "successfully completed.")

            agents = cluster_environment.get_agents(APPLICATION)
            for svc_agent in cluster_environment.get_agents(SERVICE):
                agents.append(svc_agent)

            if len(agents) > 0:

                main_user = tenant.main.create_primaza_identity(
                    cluster_environment.name)
                kcfg = tenant.main.get_kubeconfig(main_user)

                create_secret = False
                for agent in agents:
                    error = agent.create(None, None)
                    if error:
                        logger.log_error(f"Create of {agent.type} namespace "
                                         f"{agent.name} failed: {error}")
                    elif create_secret:
                        cluster_environment.worker.\
                            create_namespaced_kubeconfig_secret(kcfg,
                                                                tenant.tenant)
                        create_secret = False

                    agent.agent.check()
                    if not settings.output_active():
                        if settings.dry_run_active():
                            print(f"Dry run create {agent.type} namespace "
                                  f"{agent.name} "
                                  "successfully completed.\n")
                        else:
                            print(f"Create {agent.type} namespace "
                                  f"{agent.name} "
                                  "successfully completed.")

        if settings.output_active():
            settings.output()
        elif settings.dry_run_active():
            print("Dry run Primaza install from options file complete.")
        else:
            print("Primaza install from options file complete.")

    except Exception as e:
        if args.verbose:
            print(traceback.format_exc())
        logger.log_error("\nAn exception occurred installing from options "
                         f"file:\n{e}")
        raise e
