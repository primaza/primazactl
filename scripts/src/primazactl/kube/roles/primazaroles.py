from kubernetes import client
from primazactl.utils import logger


# TODO: consider to split this role in 2, one for the application agent
# and one for the service agent, and to move these roles in a manifest
# in the repo primaza/primaza
def get_primaza_namespace_role(role_name: str,
                               namespace: str) -> client.V1Role:
    logger.log_entry(f"role_name: {role_name}")
    return client.V1Role(
        metadata=client.V1ObjectMeta(
            name=role_name,
            namespace=namespace,
            labels={"app.kubernetes.io/component": "coreV1",
                    "app.kubernetes.io/created-by": "primaza",
                    "app.kubernetes.io/instance": role_name.replace(":", "-"),
                    "app.kubernetes.io/managed-by": "primazactl",
                    "app.kubernetes.io/name": "rolebinding",
                    "app.kubernetes.io/part-of": "primaza"}),
        rules=[
            # shared
            client.V1PolicyRule(
                api_groups=["apps"],
                resources=["deployments"],
                verbs=["create"]),
            client.V1PolicyRule(
                api_groups=[""],
                resources=["configmaps"],
                verbs=["create"]),
            client.V1PolicyRule(
                api_groups=[""],
                resources=["secrets"],
                verbs=[
                    "get", "list",  # shared
                    "create", "update", "delete",  # application namespace
                    "watch",  # service namespace (pull strategy)
                ]),

            # application namespace
            client.V1PolicyRule(
                api_groups=["apps"],
                resources=["deployments"],
                verbs=["delete", "get", "update"],
                resource_names=["primaza-app-agent"]),
            client.V1PolicyRule(
                api_groups=["primaza.io"],
                resources=["servicebindings", "servicecatalogs"],
                verbs=["get", "list", "watch", "create", "update", "delete"]),
            client.V1PolicyRule(
                api_groups=[""],
                resources=["configmaps"],
                verbs=["get", "list", "update", "delete"],
                resource_names=["primaza-agentapp-config"]),
            # pull synchronization strategy
            client.V1PolicyRule(
                api_groups=["primaza.io"],
                resources=["serviceclaims"],
                verbs=["get", "list", "watch"]),

            # service namespace
            client.V1PolicyRule(
                api_groups=["apps"],
                resources=["deployments"],
                verbs=["delete", "get", "update"],
                resource_names=["primaza-svc-agent"]),
            client.V1PolicyRule(
                api_groups=[""],
                resources=["configmaps"],
                verbs=["get", "list", "update", "delete"],
                resource_names=["primaza-agentsvc-config"]),
            client.V1PolicyRule(
                api_groups=["primaza.io"],
                resources=["serviceclasses"],
                verbs=["get", "list", "watch", "create", "update",
                       "patch", "delete"]),
            # pull synchronization strategy
            client.V1PolicyRule(
                api_groups=["primaza.io"],
                resources=["registeredservices"],
                verbs=["get", "list", "watch"]),
        ])
