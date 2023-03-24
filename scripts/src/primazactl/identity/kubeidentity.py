import polling2
import yaml
from typing import Dict
from kubernetes import client
from primazactl.utils import logger
from primazactl.utils.kubeconfigwrapper import KubeConfigWrapper


def get_identity_kubeconfig(
        kubeconfig: KubeConfigWrapper,
        identity: str,
        serverUrl: str | None) -> str:
    """
        Generates the kubeconfig for the Identity (Service Account) `identity`.

        :type kubeconfig: KubeConfigWrapper
        :param kubeconfig: Kubeconfig to use to connect to the cluster
        :type identity: str
        :param identity: The name of the identity
        :type serverUrl: str | None
        :param serverUrl: Overwrite the generated kubeconfig's server URL
        :rtype: str
        :return kubeconfig: The kubeconfig as string
    """
    logger.log_entry(f"csr name: {identity}")

    api_client = kubeconfig.get_api_client()
    idauth = get_identity_token(api_client, identity)

    kcw = kubeconfig.get_kube_config_for_cluster()
    kcd = kcw.get_kube_config_content_as_yaml()
    kcd["contexts"][0]["context"]["user"] = identity
    kcd["users"][0]["name"] = identity
    kcd["users"][0]["user"]["token"] = idauth["token"]

    if serverUrl is not None:
        kcd["clusters"][0]["cluster"]["server"] = serverUrl

    logger.log_info(f"kubeconfig:\n{yaml.dump(kcd)}")

    return yaml.dump(kcd)


def get_identity_token(
        api_client: client.ApiClient,
        identity: str,
        timeout: int = 60) -> Dict[str, str]:
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
    corev1 = client.CoreV1Api(api_client)

    secret = polling2.poll(
        target=lambda: corev1.read_namespaced_secret(
            name=f"{identity}-key",
            namespace="kube-system"),
        check_success=lambda x:
        x.data is not None and x.data["token"] is not None,
        step=1,
        timeout=timeout,
    )
    return secret.data


def create_identity(
        api_client: client.ApiClient,
        namespace: str,
        identity: str):
    """
        Creates the Identity `identity` in the provided namespace

        :type kubeconfig: KubeConfigWrapper
        :param kubeconfig: Kubeconfig to use to connect to the cluster
        :type identity: str
        :param identity: The name of the identity
        :type namespace: str
        :param namespace: Namespace where to create the identity
    """
    corev1 = client.CoreV1Api(api_client)

    sa = client.V1ServiceAccount(
        metadata=client.V1ObjectMeta(name=identity))
    corev1.create_namespaced_service_account(namespace, sa)

    sa = corev1.read_namespaced_service_account(
        name=identity,
        namespace=namespace)
    ownership = client.V1OwnerReference(
        api_version=sa.api_version,
        kind=sa.kind,
        name=sa.metadata.name,
        uid=sa.metadata.uid)

    id_key = client.V1Secret(
        metadata=client.V1ObjectMeta(
            name=f"{identity}-key",
            namespace=namespace,
            owner_references=[ownership],
            annotations={
                "kubernetes.io/service-account.name": sa.metadata.name,
            },
        ),
        type="kubernetes.io/service-account-token",)
    corev1.create_namespaced_secret(namespace, id_key)
