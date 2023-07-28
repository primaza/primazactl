import os
from primazactl.primazaworker.workercluster import WorkerCluster
from primazactl.cmd.create.namespace.constants import APPLICATION
from primazactl.utils import logger
from .utils import expand_path
from .defaults import defaults
from .tenant import Tenant
from .agent import Agent


class ClusterEnvironment(object):

    options: {} = None
    name: str = None
    context: str = None
    environment: str = None
    kube_config: str = None
    manifest: str = None
    version: str = None
    tenant: Tenant = None
    worker: WorkerCluster = None
    internal_url: str = None

    def __init__(self, options, tenant):

        logger.log_entry()

        self.options = options
        self.tenant = tenant

        if "name" in options:
            self.name = options["name"]

        if "environment" in self.options:
            self.environment = self.options["environment"]

        if "targetCluster" in self.options:
            target_cluster = self.options["targetCluster"]
            if "kubeconfig" in target_cluster:
                self.kube_config = expand_path(target_cluster["kubeconfig"])
            if "context" in target_cluster:
                self.context = target_cluster["context"]
            if "internalUrl" in target_cluster:
                self.internal_url = target_cluster["internalUrl"]

        if tenant.manifest_directory:
            self.manifest = os.path.join(tenant.manifest_directory,
                                         defaults["worker_config"])

        self.version = tenant.version if tenant.version \
            else defaults["version"]

        logger.log_info(f"Cluster Environment created: {self.name}")

    def join(self, name, context, kubeconfig, environment,
             manifest, version, internal_url):

        self.add_args(name, context, kubeconfig, environment,
                      manifest, version, internal_url)

        logger.log_info(self.name)

        if not self.name:
            return "Join cluster requires a cluster environment name."
        elif not self.environment:
            return "Join cluster requires an environment name."
        else:
            self.worker = WorkerCluster(
                    primaza_main=self.tenant.main,
                    context=self.context,
                    kubeconfig_file=self.kube_config,
                    config_file=self.manifest,
                    version=self.version,
                    environment=self.environment,
                    cluster_environment=self.name,
                    tenant=self.tenant.tenant,
                    internal_url=self.internal_url
                )
            self.worker.install_worker()
            return ""

    def create_only(self, name, context, kubeconfig):

        self.add_args(name, context, kubeconfig, None, None, None, None)
        if not self.name:
            return "Namespace create requires a cluster environment name."
        else:
            self.worker = WorkerCluster(
                primaza_main=self.tenant.main,
                context=self.context,
                kubeconfig_file=self.kube_config,
                config_file=None,
                version=None,
                environment=None,
                cluster_environment=self.name,
                tenant=self.tenant.tenant,
                internal_url=None,
            )

    def add_args(self, name, context, kubeconfig, environment,
                 manifest, version, internal_url):

        if name:
            self.name = name

        if context:
            self.context = context

        if environment:
            self.environment = environment

        if manifest:
            self.manifest = manifest

        if version:
            self.version = version

        if kubeconfig:
            self.kube_config = expand_path(kubeconfig)

        if internal_url:
            self.internal_url = internal_url

    def get_agents(self,  type):
        agents = []
        cluster_env = self.options
        if type == APPLICATION:
            if "applicationNamespaces" in self.options:
                for agent in cluster_env["applicationNamespaces"]:
                    agents.append(Agent(agent["name"], type, self))
        else:
            if "serviceNamespaces" in self.options:
                for agent in cluster_env["serviceNamespaces"]:
                    agents.append(Agent(agent["name"], type, self))
        return agents

    def get_agent(self, name, type):

        return Agent(name, type, self)
