import yaml
from primazactl.utils import logger
from .tenant import Tenant
from .cluster_environment import ClusterEnvironment
from .defaults import defaults

#  apiVersion: primaza.io/v1alpha1
#  kind: Tenant
#  name: alice
#  kubeconfig: ~/.kube/config
#  context: primaza
#  version: latest
#  manifest_directory: ./out/config
#  clusterEnvironments:
#    - name: onprem-cluster
#      environment: dev
#      targetCluster:
#           kubeconfig: ~/.kube/config
#           context: onprem
#      applicationNamespaces:
#           - name: alice-app
#      serviceNamespaces:
#           - name: alice-svc
#    - name: aws-cluster
#      environment: dev
#      targetCluster:
#           kubeconfig: ~/.kube/config-aws
#           context: aws
#      ["applicationNamespaces:"]
#           - name: aws-app
#       serviceNamespaces:
#           - name: aws-svc

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
                    logger.log_warning("Invalid \'kind\' value in options "
                                       "file, options file will be ignored")
            else:
                logger.log_warning("Invalid \'apiVersion\' value in options "
                                   "file, options file will be ignored")
        else:
            logger.log_info("no options file")
            self.options = {}

    def get_options(self):
        return self.options

    def get_tenant(self):
        return Tenant(self.options)

    def get_cluster_environments(self, tenant):
        cluster_environments = []
        if "clusterEnvironments" in self.options:
            for cluster_environment in self.options["clusterEnvironments"]:
                cluster_environments.append(
                    ClusterEnvironment(cluster_environment, tenant))
        return cluster_environments

    def get_cluster_environment(self, name, tenant):
        if name:
            if "clusterEnvironments" in self.options:
                for cluster_environment in self.options["clusterEnvironments"]:
                    if "name" in cluster_environment and \
                            name == cluster_environment["name"]:
                        return ClusterEnvironment(cluster_environment, tenant)
                logger.log_error(f"cluster environment {name} not found in "
                                 f"options file")
            else:
                cluster_environment = ClusterEnvironment({}, tenant)
                cluster_environment.name = name
                return cluster_environment
        else:
            cluster_environment = ClusterEnvironment({}, tenant)
            return cluster_environment
