from kubernetes import client
from primazactl.utils import logger


def get_worker_role(user: str) -> client.V1ClusterRole:
    logger.log_entry(f"user: {user}")
    return client.V1ClusterRole(
        metadata=client.V1ObjectMeta(name=user),
        rules=[
            client.V1PolicyRule(
                api_groups=[""],
                resources=["pods"],
                verbs=["list", "get", "create"]),
            client.V1PolicyRule(
                api_groups=[""],
                resources=["secrets"],
                verbs=["create"]),
            client.V1PolicyRule(
                api_groups=["primaza.io/v1alpha1"],
                resources=["servicebindings"],
                verbs=["create"]),
        ])


def get_primaza_namespace_role(user: str) -> client.V1ClusterRole:
    logger.log_entry(f"user: {user}")
    return client.V1ClusterRole(
        metadata=client.V1ObjectMeta(name=user),
        rules=[
            client.V1PolicyRule(
                api_groups=["apps"],
                resources=["deployments"],
                verbs=["create"]),
            client.V1PolicyRule(
                api_groups=["apps"],
                resources=["deployments"],
                verbs=["delete"],
                resource_names=["primaza-controller-agentapp",
                                "primaza-controller-agentsvc"]),
            client.V1PolicyRule(
                api_groups=["primaza.io"],
                resources=["servicebindings", "serviceclasses"],
                verbs=["get", "list", "watch", "create", "update",
                       "patch", "delete"])
        ])
