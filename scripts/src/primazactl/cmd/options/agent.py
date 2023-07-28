import os
from primazactl.cmd.create.namespace.constants import APPLICATION
from primazactl.primazaworker.workernamespace import WorkerNamespace
from primazactl.utils import logger
from .tenant import Tenant
from .defaults import defaults


class Agent(object):

    type = None
    cluster_environment = None
    tenant: Tenant = None
    name: str = None
    manifest: str = None
    version: str = None
    agent: WorkerNamespace = None

    def __init__(self, name, type, cluster_environment):

        logger.log_entry(name)

        self.cluster_environment = cluster_environment

        self.tenant = cluster_environment.tenant

        self.name = name

        self.type = type

        if self.tenant.manifest_directory:
            if type == APPLICATION:
                self.manifest = os.path.join(self.tenant.manifest_directory,
                                             defaults["app_agent_config"])
            else:
                self.manifest = os.path.join(self.tenant.manifest_directory,
                                             defaults["service_agent_config"])

        self.version = self.tenant.version if self.tenant.version \
            else defaults["version"]

        logger.log_info(f"Agent created: {self.name}")

    def create(self, manifest, version):

        logger.log_info(f"{self.type}:{self.name}")

        if manifest:
            self.manifest = manifest

        if version:
            self.version = version

        if not self.tenant.tenant:
            return f"{self.type} namespace create requires a " \
                   f"cluster tenant name."
        if not self.cluster_environment.name:
            return f"{self.type} namespace create requires a " \
                   f"cluster environment name."

        logger.log_info("Create WorkerNamespace")
        self.agent = WorkerNamespace(self.type,
                                     self.name,
                                     self.cluster_environment.name,
                                     self.cluster_environment.context,
                                     self.cluster_environment.kube_config,
                                     self.manifest,
                                     self.version,
                                     self.tenant.main,
                                     self.cluster_environment.worker)
        logger.log_info("Create Agent")
        self.agent.create()
        return None
