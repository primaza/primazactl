import base64
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
    sa_name: str = None
    key_name: str = None
    namespace: str = None
    tenant: str = None

    def __init__(self, api_client: client,
                 sa_name: str,
                 key_name: str,
                 namespace: str,
                 tenant: str,
                 ):
        self.api_client = api_client
        self.sa_name = sa_name
        self.key_name = key_name
        self.namespace = namespace
        self.tenant = tenant

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
        logger.log_entry(f"sa name: {self.sa_name}, "
                         f"namespace: {self.namespace}")

        idauth = self.get_token()

        kcw = kubeconfig.get_kube_config_for_cluster()
        kcd = kcw.get_kube_config_content_as_yaml()
        del kcd["users"]

        kcd["contexts"][0]["context"]["user"] = self.sa_name
        kcd["users"] = [
                {"name": self.sa_name, "user": {"token": idauth["token"]}}]

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
        logger.log_entry(f"sa_name: {self.sa_name} "
                         f"namespace: {self.namespace}")
        corev1 = client.CoreV1Api(self.api_client)

        secret = polling2.poll(
            target=lambda: corev1.read_namespaced_secret(
                name=self.key_name,
                namespace=self.namespace),
            check_success=lambda x:
            x.data is not None and x.data["token"] is not None,
            step=1,
            timeout=timeout,
        )

        data = {}
        for k, v in secret.data.items():
            data[k] = base64.b64decode(v.encode("utf-8")).decode("utf-8")
        return data

    def create(self):

        logger.log_entry(f"sa_name: {self.sa_name} "
                         f"namespace: {self.namespace}")

        service_account = ServiceAccount(self.api_client,
                                         self.sa_name,
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
                name=self.key_name,
                namespace=self.namespace,
                owner_references=[ownership],
                annotations={
                    "kubernetes.io/service-account.name": sa.metadata.name,
                },
            ),
            type="kubernetes.io/service-account-token",)
        secret = Secret(self.api_client, self.key_name,
                        self.namespace, self.tenant, None)
        secret.create(id_key)
