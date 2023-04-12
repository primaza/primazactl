import polling2
import yaml
from typing import Dict
from kubernetes import client
from primazactl.utils import logger
from primazactl.utils.kubeconfigwrapper import KubeConfigWrapper
from primazactl.kube.serviceaccount import ServiceAccount
from primazactl.kube.secret import Secret


class KubeIdentity(object):

    api_client: client = None
    identity: str = None
    namespace: str = None

    def __init__(self, api_client: client, identity: str, namespace: str,):
        self.api_client = api_client
        self.identity = identity
        self.namespace = namespace

    def get_kubeconfig(self,
                       kubeconfig: KubeConfigWrapper,
                       serverUrl: str | None) -> str:
        """
            Generates the kubeconfig for the Identity (Service Account)
            `identity`.

            :type kubeconfig: KubeConfigWrapper
            :param kubeconfig: Kubeconfig to use to connect to the cluster
            :type identity: str
            :param identity: The name of the identity
            :type serverUrl: str | None
            :param serverUrl: Overwrite the generated kubeconfig's server URL
            :rtype: str
            :return kubeconfig: The kubeconfig as string
        """
        logger.log_entry(f"csr name: {self.identity}, "
                         f"namespace: {self.namespace}")

        idauth = self.get_token()

        kcw = kubeconfig.get_kube_config_for_cluster()
        kcd = kcw.get_kube_config_content_as_yaml()
        kcd["contexts"][0]["context"]["user"] = self.identity
        kcd["users"][0]["name"] = self.identity
        kcd["users"][0]["user"]["token"] = idauth["token"]

        if serverUrl is not None:
            kcd["clusters"][0]["cluster"]["server"] = serverUrl

        return yaml.dump(kcd)

    def get_token(self, timeout: int = 60) -> Dict[str, str]:
        """
            Retrieves the Identity's token: the data in the Service Account's
            Secret.

            :type kubeconfig: KubeConfigWrapper
            :param kubeconfig: Kubeconfig to use to connect to the cluster
            :type identity: str
            :param identity: The name of the identity
            :type timeout: int
            :param timeout: Max time to wait for token to be generated
            :rtype: Dict[str, str]
            :return token: A dictionary with Secret data: token, ca.crt,
                            and namespace
        """
        logger.log_entry(f"identity: {self.identity} "
                         f"namespace: {self.namespace}")
        corev1 = client.CoreV1Api(self.api_client)

        secret = polling2.poll(
            target=lambda: corev1.read_namespaced_secret(
                name=f"{self.identity}-key",
                namespace=self.namespace),
            check_success=lambda x:
            x.data is not None and x.data["token"] is not None,
            step=1,
            timeout=timeout,
        )
        return secret.data

    def create(self):

        """
            Creates the Identity `identity` in the provided namespace

            :type kubeconfig: KubeConfigWrapper
            :param kubeconfig: Kubeconfig to use to connect to the cluster
            :type identity: str
            :param identity: The name of the identity
            :type namespace: str
            :param namespace: Namespace where to create the identity
        """
        logger.log_entry(f"identity: {self.identity} "
                         f"namespace: {self.namespace}")

        service_account = ServiceAccount(self.api_client,
                                         self.identity,
                                         self.namespace)
        service_account.create()
        sa = service_account.read()

        ownership = client.V1OwnerReference(
            api_version=sa.api_version,
            kind=sa.kind,
            name=sa.metadata.name,
            uid=sa.metadata.uid)

        id_key = client.V1Secret(
            metadata=client.V1ObjectMeta(
                name=f"{self.identity}-key",
                namespace=self.namespace,
                owner_references=[ownership],
                annotations={
                    "kubernetes.io/service-account.name": sa.metadata.name,
                },
            ),
            type="kubernetes.io/service-account-token",)
        secret = Secret(self.api_client, f"{self.identity}-key",
                        self.namespace, None)
        secret.create(id_key)
