import yaml
import uuid
from typing import Dict
from kubernetes import client
from primazactl.utils import logger
from primazactl.utils.command import Command
from primazactl.identity.kubeidentity import KubeIdentity
from primazactl.kube.secret import Secret
from primazactl.kube.role import Role
from primazactl.kube.access.accessreview import AccessReview
from primazactl.utils import kubeconfig
from primazactl.utils.kubeconfigwrapper import KubeConfigWrapper
from primazactl.utils import names
from primazactl.utils import settings


class PrimazaCluster(object):

    namespace: str = None
    context: str = None
    user: str = None
    user_type: str = None
    kube_config_file: str = None
    kubeconfig: KubeConfigWrapper = None
    config_file: str = None
    cluster_environment: str = None
    tenant: str = None

    def __init__(self, namespace, context,
                 user, user_type,
                 kubeconfig_path, config_file,
                 cluster_environment,
                 tenant):
        self.namespace = namespace
        self.context = context
        self.user = user
        self.user_type = user_type if user_type else user
        self.config_file = config_file
        self.cluster_environment = cluster_environment
        self.tenant = tenant

        self.kube_config_file = kubeconfig_path \
            if kubeconfig_path is not None \
            else kubeconfig.from_env()

        kcw = KubeConfigWrapper(context, self.kube_config_file)
        self.kubeconfig = kcw.get_kube_config_for_cluster()

    def get_updated_server_url(self):
        logger.log_entry()
        cluster = f'{self.context.replace("kind-","")}'
        control_plane = f'{cluster}-control-plane'
        out, err = Command().run(f"docker inspect {control_plane}")
        if err != 0:
            raise RuntimeError("\n[ERROR] error getting data from docker:"
                               f"{control_plane} : {err}")

        docker_data = yaml.safe_load(out)
        try:
            networks = docker_data[0]["NetworkSettings"]["Networks"]
            ipaddr = networks["kind"]["IPAddress"]
            logger.log_info(f"new cluster url: https://{ipaddr}:6443")
            return f"https://{ipaddr}:6443"
        except KeyError:
            logger.log_info("new cluster url not found")
            return ""

    def get_kubeconfig(self, identity: KubeIdentity,
                       other_context) -> Dict:
        logger.log_entry(f"id: {identity.sa_name}, "
                         f"other_context: {other_context}")
        server_url = self.get_updated_server_url() \
            if self.context != other_context \
            else None

        return identity.get_kubeconfig(self.kubeconfig, server_url)

    def create_identity(self, sa_name: str, key_name: str) -> KubeIdentity:
        logger.log_entry()
        api_client = self.kubeconfig.get_api_client()
        identity = KubeIdentity(api_client, sa_name,
                                key_name, self.namespace, self.tenant)
        identity.create()
        return identity

    def create_namespaced_kubeconfig_secret(
            self,
            kubeconfig: str,
            tenant: str,
            cluster_environment: str = None,
            secret_name: str = None):
        """
        Creates the Primaza's secret
        """
        user_type = cluster_environment \
            if cluster_environment \
            else self.user_type
        secret_name = secret_name \
            if secret_name \
            else names.get_kube_secret_name(user_type)

        logger.log_entry(f"user_type: {user_type}, "
                         f"namespace: {self.namespace}")
        api_client = self.kubeconfig.get_api_client()
        secret = Secret(api_client, secret_name,
                        self.namespace, kubeconfig, tenant)

        if cluster_environment is not None:
            if settings.dry_run_active():
                secret.owners = [client.V1OwnerReference(
                    api_version="primaza.io/v1alpha",
                    kind="cluster_environment",
                    name="dry_run",
                    uid=str(uuid.uuid4()))]
            else:
                owner = self.read_clusterenvironment(tenant,
                                                     cluster_environment)
                secret.owners = [client.V1OwnerReference(
                    api_version=owner["apiVersion"],
                    kind=owner["kind"],
                    name=owner["metadata"]["name"],
                    uid=owner["metadata"]["uid"])]

        secret.create()
        return secret_name

    def kubeconfig(self) -> KubeConfigWrapper:
        return KubeConfigWrapper(self.context, self.kube_config_file)

    def check_service_account_roles(self, service_account_name,
                                    role_name, role_namespace):
        logger.log_entry(self.namespace)
        if settings.dry_run_active():
            return []

        api_client = self.kubeconfig.get_api_client()
        ar = AccessReview(api_client,
                          service_account_name,
                          self.namespace,
                          role_namespace)
        role = Role(api_client,
                    role_name, role_namespace, None)
        rules = role.get_rules()
        error_messages = []
        for rule in rules:
            error_message = ar.check_access(rule)
            if error_message:
                error_messages.extend(error_message)
        return error_messages

    def install_config(self, manifest):
        manifest.apply(self.kubeconfig.get_api_client(), "create")

    def uninstall_config(self, manifest):
        manifest.apply(self.kubeconfig.get_api_client(), "delete")

    def read_clusterenvironment(self, namespace: str,
                                cluster_environment_name: str) -> Dict:
        return self.read_custom_object(
            namespace=namespace,
            group="primaza.io",
            version="v1alpha1",
            plural="clusterenvironments",
            name=cluster_environment_name)

    def read_custom_object(self, namespace: str, group: str, version: str,
                           plural: str, name: str) -> Dict:
        api_client = self.kubeconfig.get_api_client()
        cobj = client.CustomObjectsApi(api_client)

        return cobj.get_namespaced_custom_object(
            namespace=namespace,
            group=group,
            version=version,
            plural=plural,
            name=name)
