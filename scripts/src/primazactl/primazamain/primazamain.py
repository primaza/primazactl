from typing import Tuple
from primazactl.utils import kubeconfigwrapper
from primazactl.utils import primazaconfig
from primazactl.utils import logger
from kubernetes import client
import polling2
import yaml
from primazactl.utils.command import Command
from primazactl.utils.kubeconfigwrapper import KubeConfigWrapper
from primazactl.utils import kubeconfig
from primazactl.primazamain.constants import PRIMAZA_NAMESPACE


class PrimazaMain(object):
    kubeconfig: kubeconfigwrapper.KubeConfigWrapper = None
    kube_config_file: str

    cluster_name: str

    primaza_config: str | None = None
    primaza_version: str | None = None

    def __init__(
            self,
            cluster_name: str | None,
            kubeconfig_path: str | None,
            config_file: str | None,
            version: str | None):

        self.kube_config_file = kubeconfig_path \
            if kubeconfig_path is not None \
            else kubeconfig.from_env()

        self.cluster_name = cluster_name \
            if cluster_name is not None \
            else KubeConfigWrapper(None, self.kube_config_file).get_context()

        self.primaza_config = config_file
        self.primaza_version = version

        kcw = KubeConfigWrapper(cluster_name, self.kube_config_file)
        self.kubeconfig = kcw.get_kube_config_for_cluster()

        logger.log_info("Primaza main created for cluster "
                        f"{self.cluster_name}")

    def install_primaza(self):
        out, err = self.kubectl_do(f"apply -f {self.primaza_config}")
        if err == 0:
            logger.log_entry("Install and configure primaza completed")

        logger.log_info(out)
        if err != 0:
            raise RuntimeError(
                "error deploying Primaza's controller into "
                f"cluster {self.cluster_name}")

    def create_clustercontext_secret(self, secret_name: str, kubeconfig: str):
        """
        Creates the Primaza's ClusterContext secret
        """
        api_client = self.kubeconfig.get_api_client()
        corev1 = client.CoreV1Api(api_client)

        secret = client.V1Secret(
            metadata=client.V1ObjectMeta(
                name=secret_name, namespace=PRIMAZA_NAMESPACE),
            string_data={"kubeconfig": kubeconfig})

        logger.log_info("create_namespaced_secret")
        corev1.create_namespaced_secret(
            namespace=PRIMAZA_NAMESPACE, body=secret)

    def write_resource(self, resource, kcw=None):
        logger.log_entry()
        if not kcw:
            kcw = self.kubeconfig
        resource_config = primazaconfig.PrimazaConfig()
        resource_config.set_content(resource)
        resource_config.apply(kcw)

    def write_cluster_environment(self,
                                  cluster_environment_name,
                                  environment_name,
                                  secret_name):

        logger.log_entry("kind: ClusterEnvironment, "
                         f"name: {cluster_environment_name}, "
                         f"environment_name: {environment_name} "
                         f"secret_name: {secret_name}")

        resource = {
            "apiVersion": "primaza.io/v1alpha1",
            "kind": "ClusterEnvironment",
            "metadata": {
                "name": cluster_environment_name,
                "namespace": PRIMAZA_NAMESPACE,
            },
            "spec": {
                "environmentName": environment_name,
                "clusterContextSecret": secret_name,
            }
        }
        kcw = self.kubeconfig.get_kube_config_for_cluster()

        logger.log_info(f"write cluster environment:\n{yaml.dump(resource)}")
        self.write_resource(yaml.dump(resource), kcw=kcw)

    def check_state(self, ce_name, state, timeout=60):

        logger.log_entry(f"check state, ce_name: {ce_name}, state:{state}")
        api_client = self.kubeconfig.get_api_client()
        cobj = client.CustomObjectsApi(api_client)

        try:
            polling2.poll(
                target=lambda: cobj.get_namespaced_custom_object_status(
                    group="primaza.io",
                    version="v1alpha1",
                    namespace="primaza-system",
                    plural="clusterenvironments",
                    name=ce_name).get("status", {}).get("state", None),
                check_success=lambda x: x is not None and x == state,
                step=5,
                timeout=timeout)
        except polling2.TimeoutException:
            ce_status = cobj.get_namespaced_custom_object_status(
                group="primaza.io",
                version="v1alpha1",
                namespace="primaza-system",
                plural="clusterenvironments",
                name=ce_name)
            logger.log_error("Timed out waiting for cluster environment "
                             f"{ce_name}. State was {state}")
            logger.log_error(f"environment: \n{yaml.dump(ce_status)}")
            raise RuntimeError("[ERROR] Timed out waiting for cluster "
                               f"environment: {ce_name} state: {state}")

    def check_status_condition(self, ce_name: str, ctype: str, cstatus: str):
        logger.log_entry(f"check status condition, ce_name: {ce_name},"
                         f"type: {ctype}, status {cstatus}")
        api_client = self.kubeconfig.get_api_client()
        cobj = client.CustomObjectsApi(api_client)

        ce_status = cobj.get_namespaced_custom_object_status(
            group="primaza.io",
            version="v1alpha1",
            namespace="primaza-system",
            plural="clusterenvironments",
            name=ce_name)
        ce_conditions = ce_status.get("status", {}).get("conditions", None)
        if ce_conditions is None or len(ce_conditions) == 0:
            logger.log_error("Cluster Environment status conditions are "
                             "empty or not defined")
            raise RuntimeError("[ERROR] checking install: Cluster Environment "
                               "status conditions are empty or not defined")

        logger.log_info(f"\n\nce conditions:\n{ce_conditions}")

        for condition in ce_conditions:
            if condition["type"] == ctype:
                if condition["status"] != cstatus:
                    message = f'Cluster Environment condition type {ctype} ' \
                              f'does not have expected status: {cstatus}, ' \
                              f'status was {condition["status"]}'
                    logger.log_error(message)
                    raise RuntimeError(f'[ERROR] {message}')
                return

        message = f'Cluster Environment condition type {ctype} ' \
                  'was not found'
        logger.log_error(message)
        raise RuntimeError(f'[ERROR] {message}')

    def uninstall_primaza(self):
        out, err = self.kubectl_do(f"delete -f {self.primaza_config}")
        print(out)

        if err != 0:
            raise RuntimeError(
                "error deleting Primaza's controller from "
                f"cluster {self.cluster_name} : {err}")

    def kubeconfig(self) -> KubeConfigWrapper:
        return KubeConfigWrapper(self.cluster_name, self.kube_config_file)

    def kubectl_do(self, cmd: str) -> Tuple[str, int]:
        return Command().run(
            "kubectl"
            f" --kubeconfig {self.kube_config_file}"
            f" --context {self.cluster_name}"
            f" {cmd}")
