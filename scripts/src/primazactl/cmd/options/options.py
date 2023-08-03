import yaml
from primazactl.utils import logger
from .tenant import Tenant
from .cluster_environment import ClusterEnvironment
from .defaults import defaults


API_VERSION: str = "apiVersion"
KIND: str = "kind"


class Options(object):

    options: {} = None
    options_empty: bool = True

    def __init__(self, args):

        logger.log_info(f"Options:{args.options_file}:")

        if args.options_file:
            with open(str(args.options_file), "r") as options_content:
                load_options = yaml.safe_load(options_content)
                logger.log_info(f"loaded options: {load_options}")

            if API_VERSION in load_options and \
                    load_options[API_VERSION] == defaults["apiVersion"]:
                if KIND in load_options and load_options[KIND] \
                        == defaults["kind"]:
                    self.options = load_options
                    self.options_empty = False
                    logger.log_info(f"Option file content: {self.options}")
                else:
                    message = 'Invalid or no \'kind\' value in options ' \
                              'file, kind is required to be set to ' \
                              f'{defaults["kind"]}.'
                    logger.log_error("message")
                    raise RuntimeError(f'[ERROR] {message}')
            else:
                message = 'Invalid or no \'apiVersion\' value in options ' \
                          'file, apiVersion is required to be set to ' \
                          f'{defaults["apiVersion"]}'
                logger.log_error("message")
                raise RuntimeError(f'[ERROR] {message}')
        else:
            logger.log_info("no options file")
            self.options = {}

    def get_options(self):
        return self.options

    def get_tenant(self):
        return Tenant(self.options)

    def get_cluster_environments(self, tenant):
        cluster_environments = []
        for cluster_environment in self.options.get("clusterEnvironments", []):
            cluster_environments.append(
                    ClusterEnvironment(cluster_environment, tenant))
        return cluster_environments

    def get_cluster_environment(self, name, tenant):

        for cluster_environment in self.options.get("clusterEnvironments", []):
            if "name" in cluster_environment and \
                    name == cluster_environment["name"]:
                return ClusterEnvironment(cluster_environment, tenant)

        cluster_environment = ClusterEnvironment({}, tenant)
        cluster_environment.name = name
        return cluster_environment
