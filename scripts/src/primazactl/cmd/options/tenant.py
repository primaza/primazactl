import os
from primazactl.primazamain.maincluster import MainCluster
from primazactl.utils import logger
from .utils import expand_path
from .defaults import defaults


class Tenant(object):

    kube_config: str = None
    context: str = None
    tenant: str = None
    cluster_environments: [] = None
    version: str = None
    manifest_directory: str = None
    manifest: str = None
    main_cluster: str = None
    main: MainCluster = None
    internal_url = None

    def __init__(self, options):

        self.tenant = options["name"] if "name" in options \
            else defaults["tenant"]
        logger.log_info(f"Namespace from options: {self.tenant}")

        if "kubeconfig" in options:
            self.kube_config = expand_path(options["kubeconfig"])
            logger.log_info(f"kubeconfig from options: {self.kube_config}")
        else:
            self.kubeconfig = defaults["kubeconfig"]

        if "context" in options:
            self.context = options["context"]
            logger.log_info(f"context from options: {self.context}")

        if "manifestDirectory" in options:
            self.manifest_directory = expand_path(
                options["manifestDirectory"])
            logger.log_info("manifest directory from options: "
                            f"{self.manifest}")
            self.manifest = os.path.join(self.manifest_directory,
                                         defaults["tenant_config"])
            logger.log_info(f"calculated manifest: {self.manifest}")

        self.version = options["version"] if "version" in options \
            else defaults["version"]

        if "internalUrl" in options:
            self.internal_url = options["internalUrl"]

        logger.log_info(f"version in options: {self.version}")

    def create_only(self, context, tenant, kubeconfig, internal_url):

        self.add_args(context, tenant, kubeconfig, None, None, internal_url)

        if not self.tenant:
            error_msg = "A tenant name must be provided for join cluster " \
                        "or create of application or service namespace"
            logger.log_error(error_msg)
            return error_msg

        self.main = MainCluster(self.context, self.tenant,
                                self.kube_config, None, None, internal_url)
        return None

    def install(self, context, tenant, kubeconfig, manifest, version):

        logger.log_entry()

        self.add_args(context, tenant, kubeconfig, manifest, version, None)

        if not self.tenant:
            error_msg = "A tenant name must be provided for tenant install"
            logger.log_error(error_msg)
            return error_msg

        self.main = MainCluster(self.context,
                                self.tenant,
                                self.kube_config,
                                self.manifest,
                                self.version,
                                None)

        self.main.install_primaza()
        return None

    def add_args(self, context, tenant, kubeconfig, manifest,
                 version, internal_url):

        if context:
            self.context = context

        if tenant:
            self.tenant = tenant

        if kubeconfig:
            self.kube_config = kubeconfig

        if manifest:
            self.manifest = manifest

        if not self.manifest and version:
            self.version = version

        if internal_url:
            self.internal_url = internal_url
