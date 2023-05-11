import re
import yaml
from kubernetes import client
from kubernetes.client.rest import ApiException
from primazactl.utils import logger


def get_method(kind, action="create", namespaced=False):
    method = action
    if namespaced:
        method += "_namespaced"
    method += f"_{re.sub(r'(?<!^)(?=[A-Z])', '_', kind).lower()}"
    return method


def get_kube_client(api_version, api_client):
    group, _, version = api_version.partition("/")
    if version == "":
        version = group.capitalize()
        cap_group = "Core"
    else:
        version = version.capitalize()
        cap_group = ""
        if group.endswith(".k8s.io"):
            group = group[:-len(".k8s.io")]
        for word in group.split('.'):
            cap_group += word.capitalize()

    function = f"{cap_group}{version}Api"

    if hasattr(client, function):
        return getattr(client, function)(api_client)
    elif hasattr(client, "CustomObjectsApi"):
        return getattr(client, "CustomObjectsApi")(api_client)
    else:
        return "Not Found"


def apply_resource(resource: {}, api_client: client, action: str = "create"):

    namespace = resource["metadata"]["namespace"] \
        if "namespace" in resource["metadata"] else ""

    kwargs = {}
    if namespace:
        kwargs['namespace'] = namespace
        namespaced = True
    else:
        namespaced = False

    resource_client = get_kube_client(resource["apiVersion"], api_client)

    if isinstance(resource_client, client.CustomObjectsApi):
        group, _, version = resource["apiVersion"].partition("/")
        kwargs["group"] = group
        kwargs["version"] = version
        kwargs["plural"] = f'{resource["kind"].lower()}s'
        if action == "read":
            action = "get"
        if namespaced:
            method = f"{action}_namespaced_custom_object"
        else:
            method = f"{action}_cluster_custom_object"
    else:
        method = get_method(resource["kind"], action, namespaced)
        group, _, version = resource["apiVersion"].partition("/")

    error = ""
    if hasattr(resource_client, method):
        logger.log_info(f'call {method} on {type(resource_client)}, '
                        f'name : {resource["metadata"]["name"]}')
        if action == "create" or action == "patch":
            resp = getattr(resource_client, method)(body=resource, **kwargs)
        else:
            resource_name = resource["metadata"]["name"]
            resp = getattr(resource_client, method)(name=resource_name,
                                                    **kwargs)
    else:
        error = f"[ERROR] method {method} not found in " \
                f"{type(resource_client)}"
        logger.log_error(error)
        resp = ""

    return resp, error


def apply_manifest(resource_list, client: client,
                   action: str = "create") -> []:

    errors = []
    for resource in resource_list:
        try:
            _, error = apply_resource(resource, client, action)
            if error:
                errors.append(error)
        except ApiException as api_exception:
            body = yaml.safe_load(api_exception.body)
            if action == "create" and body["reason"] == "AlreadyExists":
                print(f'create: {body["message"]}')
            elif action == "read" and body["reason"] == "NotFound":
                print(f'read: {body["message"]}')
            elif action == "delete" and body["reason"] == "NotFound":
                print(f'delete: {body["message"]}')
            else:
                errors.append(f'[ERROR] {action}: {body["message"]}')
    return errors
