import polling2
import yaml
from typing import Dict
from kubernetes import client
from primazactl.utils import logger
from primazactl.utils.kubeconfigwrapper import KubeConfigWrapper
from primazactl.kube.serviceaccount import ServiceAccount
from primazactl.kube.secret import Secret


def get_identity_kubeconfig(
        kubeconfig: KubeConfigWrapper,
        identity: str,
        namespace: str,
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
    idauth = get_identity_token(api_client, identity, namespace)

    kcw = kubeconfig.get_kube_config_for_cluster()
    kcd = kcw.get_kube_config_content_as_yaml()
    kcd["contexts"][0]["context"]["user"] = identity
    kcd["users"][0]["name"] = identity
    kcd["users"][0]["user"]["token"] = idauth["token"]

    if serverUrl is not None:
        kcd["clusters"][0]["cluster"]["server"] = serverUrl

    # logger.log_info(f"kubeconfig:\n{yaml.dump(kcd)}")

    return yaml.dump(kcd)


def get_identity_token(
        api_client: client.ApiClient,
        identity: str,
        namespace: str,
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
    logger.log_entry(f"identity: {identity}")
    corev1 = client.CoreV1Api(api_client)

    secret = polling2.poll(
        target=lambda: corev1.read_namespaced_secret(
            name=f"{identity}-key",
            namespace=namespace),
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
    logger.log_entry(f"identity: {identity}")

    service_account = ServiceAccount(api_client,
                                     identity, namespace)
    service_account.create()
    sa = service_account.read()

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
    secret = Secret(api_client, f"{identity}-key", namespace, None)
    secret.create(id_key)
