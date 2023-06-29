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


def __get_group_and_version(api_version):
    group, _, version = api_version.partition("/")
    if version == "":
        use_group = "core"
    else:
        use_group = group.lower()
    return version, use_group


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

    logger.log_entry(resource["metadata"]["name"])
    namespace = resource["metadata"]["namespace"] \
        if "namespace" in resource["metadata"] else ""

    kwargs = {}
    if namespace:
        kwargs['namespace'] = namespace
        namespaced = True
    else:
        namespaced = False

    resource_client = get_kube_client(resource["apiVersion"], api_client)

    logger.log_info(f'{resource["apiVersion"]}, {type(resource_client)}')

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


def check_self(resource_list, api_client: client,
               action: str = "create"):

    auth_client = client.AuthorizationV1Api(api_client)
    errors = []
    for resource in resource_list:
        error = __check_self_access(resource, action, auth_client)
        if len(error) > 0:
            errors.append(error)

        if resource["kind"].lower() == "customresourcedefinition":

            custom_resource = {}
            custom_resource["apiVersion"] = f'{resource["spec"]["group"]}/v1'
            custom_resource["kind"] = resource["spec"]["names"]["kind"]
            custom_resource["plural"] = resource["spec"]["names"]["plural"]
            custom_resource["metadata"] = \
                {"name": resource["metadata"]["name"],
                 "namespace": "kube-system"}
            error = __check_self_access(custom_resource, action, auth_client)
            if len(error) > 0:
                errors.append(error)

    return errors


def __check_self_access(resource, action, auth_client):

    namespace = resource["metadata"]["namespace"] \
        if "namespace" in resource["metadata"] else ""

    version, group = __get_group_and_version(resource["apiVersion"])

    if "plural" in resource and len(resource["plural"]) > 0:
        resource_kind = resource["plural"].lower()
    else:
        resource_kind = f'{resource["kind"].lower()}s'

    body = client.V1SelfSubjectAccessReview(
        spec=client.V1SelfSubjectAccessReviewSpec(
            resource_attributes=client.V1ResourceAttributes(
                resource=resource_kind,
                verb=action,
                name=resource["metadata"]["name"]
            )
        ))
    if group and group.lower() != "core":
        body.spec.resource_attributes.group = group.lower()
    if namespace:
        body.spec.resource_attributes.namespace = namespace

    permission_failure = False
    try:
        api_response = auth_client.create_self_subject_access_review(body)
        if api_response.status.allowed:
            logger.log_info(f'User has permission to {action} '
                            f'{resource["kind"]} '
                            f'{resource["metadata"]["name"]}')
        else:
            logger.log_info(f'User does not have permission: {body}')
            permission_failure = True

    except ApiException as e:
        logger.log_info("Exception when calling AuthorizationV1Api"
                        f"->create_self_subject_access_review: {e}")
    if permission_failure:
        return [f"User does not have permissions to {action} "
                f'{resource["kind"]} ',
                f'{resource["metadata"]["name"]}"',
                "for more information use verbose output."]
    return []


def apply_manifest(resource_list, client: client,
                   action: str = "create") -> []:

    errors = check_self(resource_list, client, action)
    if len(errors) == 0:
        for resource in resource_list:
            try:
                _, error = apply_resource(resource, client, action)
                if error:
                    logger.log_error(f"FAILED: {action} of {resource} "
                                     f"failed: {error}")
                    errors.append(error)
                else:
                    logger.log_info(f'SUCCESS: {action} of '
                                    f'{resource["metadata"]["name"]} '
                                    'was successful')
            except ApiException as api_exception:
                body = yaml.safe_load(api_exception.body)
                if action == "create" and body["reason"] == "AlreadyExists":
                    logger.log_info('Already Exists: create: '
                                    f'{body["message"]}')
                    pass
                elif action == "read" and body["reason"] == "NotFound":
                    logger.log_info(f'read: {body["message"]}')
                elif action == "delete" and body["reason"] == "NotFound":
                    logger.log_info(f'delete: {body["message"]}')
                else:
                    logger.log_error('FAILED with Exception: '
                                     f'{action}: {body}')
                    errors.append('FAILED with Exception: '
                                  f'{action}: {body["message"]}')
    return errors
