

USER = "<user>"
USER_TYPE = "<user-type>"
CLUSTER_ENVIRONMENT = "<cluster-environment>"
REF_NAMESPACE = "<reference-namespace>"
REF_KUBECONFIG = "<kubeconfig-reference>"
TENANT = "<tenant>"
PROVIDER = "<provider>"

USER_TYPE_SVC = "svc"
USER_TYPE_APP = "app"
USER_TYPE_MAIN = "primaza"
USER_TYPE_WORKER = "worker"

naming_convention = {
    "identity": {
        "service_account": {
            "name": f"primaza-{TENANT}-{PROVIDER}",
            "name_user_type": f"primaza-{USER_TYPE}-{TENANT}-{PROVIDER}",
        },
        "secret": {
            "name": f"primaza-tkn-{TENANT}-{PROVIDER}",
            "name_user_type": f"primaza-tkn-{USER_TYPE}-{TENANT}-{PROVIDER}",
        },
    },
    "kubeconfig_secret": {
        "name": f"primaza-{USER_TYPE}-kubeconfig"
    },
    "role": {
        "name": f"primaza:controlplane:{USER_TYPE}"
    },
    "rolebinding": {
        "name": f"primaza:controlplane:{USER_TYPE}"
    }
}


def get_kube_secret_name(user_type):

    name = naming_convention["kubeconfig_secret"]["name"]
    return name.replace(USER_TYPE, user_type)


def get_identity_names(tenant, provider, user_type: str = None):

    identity = naming_convention["identity"]
    if user_type:
        sa = identity["service_account"]["name_user_type"]
        sa = sa.replace(USER_TYPE, user_type)
        tkn = identity["secret"]["name_user_type"]
        tkn = tkn.replace(USER_TYPE, user_type)
    else:
        sa = identity["service_account"]["name"]
        tkn = identity["secret"]["name"]

    sa = sa.replace(TENANT, tenant)
    sa = sa.replace(PROVIDER, provider)
    tkn = tkn.replace(TENANT, tenant)
    tkn = tkn.replace(PROVIDER, provider)

    return sa, tkn


def get_role_name(user_type):

    role = naming_convention["role"]["name"]
    return role.replace(USER_TYPE, user_type)


def get_rolebinding_name(user_type):

    roleb = naming_convention["rolebinding"]["name"]
    return roleb.replace(USER_TYPE, user_type)
