from kubernetes import client
from kubernetes.client.rest import ApiException
from primazactl.utils import logger
from primazactl.utils import settings


class Namespace(object):

    name: str = None
    corev1: client.CoreV1Api = None

    def __init__(self, api_client: client, name: str):
        self.name = name
        self.corev1 = client.CoreV1Api(api_client)

    def create(self):
        logger.log_entry(f"name: {self.name}")

        namespace = client.V1Namespace(
            metadata=client.V1ObjectMeta(
                name=self.name,
                labels={"app.kubernetes.io/component": "coreV1",
                        "app.kubernetes.io/created-by": "primaza",
                        "app.kubernetes.io/instance": self.name,
                        "app.kubernetes.io/managed-by": "primazactl",
                        "app.kubernetes.io/name": "secret",
                        "app.kubernetes.io/part-of": "primaza"}
            ))

        settings.add_resource(namespace.to_dict())
        if settings.dry_run == settings.DRY_RUN_CLIENT:
            return
        if not self.read():
            try:
                if settings.dry_run == settings.DRY_RUN_SERVER:
                    self.corev1.create_namespace(namespace, dry_run="All")
                else:
                    self.corev1.create_namespace(namespace)
                logger.log_info('SUCCESS: create of Namespace '
                                f'{namespace.metadata.name}',
                                settings.dry_run_active())
            except ApiException as e:
                logger.log_error('FAILED: create of Namespace '
                                 f'{namespace.metadata.name} '
                                 "Exception: %s\n" % e)
                if not settings.dry_run_active():
                    raise e
        else:
            logger.log_info('UNCHANGED: Namespace '
                            f'{namespace.name} already exists',
                            settings.dry_run_active())

    def read(self) -> client.V1Namespace | None:
        logger.log_entry(f"namespace: {self.name}")

        try:
            return self.corev1.read_namespace(name=self.name)
        except ApiException as e:
            if e.reason != "Not Found":
                logger.log_error("Exception when calling "
                                 "read_namespace: %s\n" % e)
                raise e
        return None

    def delete(self):
        logger.log_entry(f"namespace: {self.name}")

        try:
            self.corev1.delete_namespace(name=self.name)
        except ApiException as e:
            if e.reason != "Not Found":
                logger.log_error("Exception when calling "
                                 "delete_namespace: %s\n" % e)
                raise e
