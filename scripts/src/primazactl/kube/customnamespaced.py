from kubernetes import client
from kubernetes.client.rest import ApiException
import polling2
import yaml
from primazactl.utils import logger
from primazactl.utils import settings


class CustomNamespaced(object):
    custom: client = None
    name: str = None
    namespace: str = None
    body: {} = None
    group: str = None
    version: str = None
    kind: str = None
    plural: str = None

    def __init__(self, api_client,
                 group, version,
                 kind, plural,
                 name=None, namespace=None, body=None):
        self.custom = client.CustomObjectsApi(api_client)
        self.name = name
        self.namespace = namespace
        self.group = group
        self.version = version
        self.kind = kind
        self.plural = plural

        self.body = body

    def create(self):

        logger.log_entry(f"name: {self.name}, namespace: {self.namespace}")

        settings.add_resource(self.body)
        if settings.dry_run == settings.DRY_RUN_CLIENT:
            return
        if not self.read():
            try:
                if settings.dry_run == settings.DRY_RUN_SERVER:
                    self.custom.create_namespaced_custom_object(
                        self.group,
                        self.version,
                        self.namespace,
                        self.plural,
                        self.body,
                        dry_run="All")
                else:
                    self.custom.create_namespaced_custom_object(
                        self.group,
                        self.version,
                        self.namespace,
                        self.plural,
                        self.body)
                logger.log_info(f'SUCCESS: create of {self.body["kind"]} '
                                f'{self.body["metadata"]["name"]}',
                                settings.dry_run_active())
            except ApiException as e:
                body = yaml.safe_load(e.body)
                logger.log_error(f'FAILED: create of {self.body["kind"]} '
                                 f'{self.body["metadata"]["name"]} '
                                 f'Exception: {body}')
                if not settings.dry_run_active():
                    raise e
        else:
            logger.log_info(f'UNCHANGED: {self.body["kind"]} '
                            f'{self.body["metadata"]["name"]} already exists',
                            settings.dry_run_active())

    def read(self) -> client.V1Namespace | None:
        logger.log_entry(f"name: {self.name}, namespace: {self.namespace}")

        try:
            return self.custom.get_namespaced_custom_object(self.group,
                                                            self.version,
                                                            self.namespace,
                                                            self.plural,
                                                            self.name)
        except ApiException as e:
            if e.reason != "Not Found":
                logger.log_error("Exception when calling "
                                 "get_namespaced_custom_object: %s\n" % e)
                raise e
        return None

    def delete(self):
        logger.log_entry(f"namespace: {self.name}")

        try:
            self.custom.delete_namespaced_custom_object(self.group,
                                                        self.version,
                                                        self.namespace,
                                                        self.plural,
                                                        self.name)
        except ApiException as e:
            if e.reason != "Not Found":
                logger.log_error("Exception when calling "
                                 "delete_namespace: %s\n" % e)
                raise e

    def find(self):
        logger.log_entry(f"namespace: {self.name}")

        try:
            obj = self.custom.get_namespaced_custom_object(
                    self.group,
                    self.version,
                    self.namespace,
                    self.plural,
                    self.name)
            self.body = obj
            self.name = self.body["metadata"]["name"]
            self.namespace = self.body["metadata"]["namespace"]
            logger.log_info(f"found: {self.name} in "
                            f"namespace {self.namespace}")

        except ApiException as e:
            if e.reason != "Not Found":
                logger.log_error("Exception when calling "
                                 "delete_namespace: %s\n" % e)
                raise e

    def patch(self, body):
        logger.log_entry(f"type: {self.name}, namespace: {self.namespace}")

        try:
            self.body = self.custom.patch_namespaced_custom_object(
                self.group,
                self.version,
                self.namespace,
                self.plural,
                self.name,
                body)
        except ApiException as e:
            logger.log_error("Exception when calling "
                             "replace_namespaced_custom_object: %s\n" % e)
            raise e

    def check_state(self, state):

        logger.log_entry(f"check state, ce_name: {self.name}, state:{state}")

        try:
            polling2.poll(
                target=lambda: self.custom.get_namespaced_custom_object_status(
                    group=self.group,
                    version=self.version,
                    namespace=self.namespace,
                    plural=self.plural,
                    name=self.name).get("status", {}).get("state", None),
                check_success=lambda x: x is not None and x == state,
                step=5,
                timeout=60)
        except polling2.TimeoutException:
            ce_status = self.custom.get_namespaced_custom_object_status(
                group=self.group,
                version=self.version,
                namespace=self.namespace,
                plural=self.plural,
                name=self.name)
            logger.log_error("Timed out waiting for cluster environment "
                             f"{self.name} to reach state {state}")
            logger.log_error(f"environment: \n{yaml.dump(ce_status)}")
            raise RuntimeError("[ERROR] Timed out waiting for cluster "
                               f"environment: {self.name} state: {state}")

    def check_status_condition(self, ctype: str, cstatus: str):
        logger.log_entry(f"check status condition, ce_name: {self.name},"
                         f"type: {ctype}, status {cstatus}")

        ce_status = self.custom.get_namespaced_custom_object_status(
            group=self.group,
            version=self.version,
            namespace=self.namespace,
            plural=self.plural,
            name=self.name)

        ce_conditions = ce_status.get("status", {}).get("conditions", None)
        if ce_conditions is None or len(ce_conditions) == 0:
            logger.log_error("Cluster Environment status conditions are "
                             "empty or not defined")
            raise RuntimeError("[ERROR] checking install: Cluster Environment "
                               "status conditions are empty or not defined")

        logger.log_info(f"\n\nce conditions:\n{ce_conditions}")

        for condition in ce_conditions:
            if condition["type"] == ctype:
                if condition["status"] != cstatus:
                    message = f'Cluster Environment condition type {ctype} ' \
                              f'does not have expected status: {cstatus}, ' \
                              f'status was {condition["status"]}'
                    logger.log_error(message)
                    raise RuntimeError(f'[ERROR] {message}')
                return

        message = f'Cluster Environment condition type {ctype} ' \
                  'was not found'
        logger.log_error(message)
        raise RuntimeError(f'[ERROR] {message}')
