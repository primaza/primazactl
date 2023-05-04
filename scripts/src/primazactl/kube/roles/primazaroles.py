from kubernetes import client
from primazactl.utils import logger


def get_primaza_namespace_role(user: str, namespace: str) -> client.V1Role:
    logger.log_entry(f"user: {user}")
    return client.V1Role(
        metadata=client.V1ObjectMeta(
            name=user,
            namespace=namespace,
            labels={"app.kubernetes.io/component": "coreV1",
                    "app.kubernetes.io/created-by": "primaza",
                    "app.kubernetes.io/instance": user.replace(":", "-"),
                    "app.kubernetes.io/managed-by": "primazactl",
                    "app.kubernetes.io/name": "rolebinding",
                    "app.kubernetes.io/part-of": "primaza"}),
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
