from typing import Tuple
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from primazactl.utils import kubeconfigwrapper
from primazactl.utils import primazaconfig
from primazactl.utils import logger
from kubernetes import client
from kubernetes.client.rest import ApiException
import polling2
import yaml
from primazactl.utils.command import Command
from primazactl.utils.kubeconfigwrapper import KubeConfigWrapper
from primazactl.utils import kubeconfig
from primazactl.primazamain.constants import PRIMAZA_NAMESPACE


class PrimazaMain(object):
    kube_config_file: str
    kube_config_file: str
    cluster_name: str

    primaza_config: str | None = None
    primaza_version: str | None = None

    certificate_private_key: bytes = None
    certificate: RSAPrivateKey = None
    namespace: str | None
    verbose: bool

    kube_config_wrapper: kubeconfigwrapper.KubeConfigWrapper = None

    def __init__(
            self,
            cluster_name: str | None,
            kubeconfig_path: str | None,
            config_file: str | None,
            version: str | None,
            private_key_file: str | None,
            namespace: str | None,
            verbose: bool = False):

        self.kube_config_file = kubeconfig_path \
            if kubeconfig_path is not None \
            else kubeconfig.from_env()

        self.cluster_name = cluster_name \
            if cluster_name is not None \
            else KubeConfigWrapper(None, self.kube_config_file).get_context()

        self.primaza_config = config_file
        self.primaza_version = version
        self.primaza_namespace = namespace if namespace \
            else PRIMAZA_NAMESPACE

        if private_key_file:
            logger.log_info(f"Read the key file : {private_key_file}")
            with open(private_key_file, "rb") as key_file:
                self.certificate = serialization.\
                    load_pem_private_key(key_file.read(), password=None)
        else:
            self.certificate = rsa.generate_private_key(public_exponent=65537,
                                                        key_size=2048)

        self.certificate_private_key = self.certificate.private_bytes(
            format=serialization.PrivateFormat.PKCS8,
            encoding=serialization.Encoding.PEM,
            encryption_algorithm=serialization.NoEncryption()).decode("utf-8")

        self.verbose = verbose

        kcw = KubeConfigWrapper(cluster_name, self.kube_config_file)
        self.kube_config_wrapper = kcw.get_kube_config_for_cluster()

        logger.log_info("Primaza main created for cluster "
                        f"{self.cluster_name}")

    def install_primaza(self):
        out, err = self.kubectl_do(f"apply -f {self.primaza_config}")
        if err == 0:
            print("Install and configure primaza completed")

        if self.verbose:
            print(out)

        if err != 0:
            raise RuntimeError(
                "error deploying Primaza's controller into "
                f"cluster {self.cluster_name}")

    def __create_certificate_signing_request(self):
        logger.log_entry()
        # Generate RSA Key and CertificateSignignRequest
        return x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u""),
            x509.NameAttribute(NameOID.LOCALITY_NAME, u""),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u'primaza'),
            x509.NameAttribute(NameOID.COMMON_NAME, u'primaza'),
        ])).add_extension(
            x509.SubjectAlternativeName([x509.DNSName(u"primaza.io")]),
            critical=False,
        ).sign(self.certificate, hashes.SHA256())

    def create_certificate_signing_request_pem(self) -> bytes:
        """
        Creates the V1CertificateSigningRequest needed for registration on
        a worker cluster
        """
        logger.log_entry()

        c = self.__create_certificate_signing_request()
        return c.public_bytes(serialization.Encoding.PEM)

    def create_clustercontext_secret(self, secret_name: str, kubeconfig: str):
        """
        Creates the Primaza's ClusterContext secret
        """
        logger.log_entry(f"Secret name: {secret_name}")

        api_client = self.kube_config_wrapper.get_api_client()
        corev1 = client.CoreV1Api(api_client)
        try:
            corev1.read_namespaced_secret(name=secret_name,
                                          namespace=self.primaza_namespace)
            corev1.delete_namespaced_secret(name=secret_name,
                                            namespace=self.primaza_namespace)
        except ApiException as e:
            if e.reason != "Not Found":
                raise e

        api_response = corev1.list_namespace()
        for item in api_response.items:
            print(f"Namespace: {item.metadata.name} is {item.status.phase}")

        logger.log_info("create secret")
        secret = client.V1Secret(
            metadata=client.V1ObjectMeta(name=secret_name),
            string_data={"kubeconfig": kubeconfig})

        logger.log_info("create_namespaced_secret")
        corev1.create_namespaced_secret(namespace=self.primaza_namespace,
                                        body=secret)

    def write_resource(self, resource, kcw=None):
        logger.log_entry()
        if not kcw:
            kcw = self.kube_config_wrapper
        resource_config = primazaconfig.PrimazaConfig()
        resource_config.set_content(resource)
        resource_config.apply(kcw)

    def write_cluster_environment(self,
                                  cluster_environment_name,
                                  environment_name,
                                  secret_name):

        logger.log_entry("kind: ClusterEnvironment, "
                         f"name: {cluster_environment_name}, "
                         f"environment_name: {environment_name} "
                         f"secret_name: {secret_name}")

        resource = {
            "apiVersion": "primaza.io/v1alpha1",
            "kind": "ClusterEnvironment",
            "metadata": {
                "name": cluster_environment_name,
                "namespace": self.primaza_namespace
            },
            "spec": {
                "environmentName": environment_name,
                "clusterContextSecret": secret_name
            }
        }
        kcw = self.kube_config_wrapper.get_kube_config_for_cluster()

        logger.log_info(f"write cluster environment:\n{yaml.dump(resource)}")
        self.write_resource(yaml.dump(resource), kcw=kcw)

    def check_state(self, ce_name, state, timeout=60):

        logger.log_entry(f"check state, ce_name: {ce_name}, state:{state}")
        api_client = self.kube_config_wrapper.get_api_client()
        cobj = client.CustomObjectsApi(api_client)

        try:
            polling2.poll(
                target=lambda: cobj.get_namespaced_custom_object_status(
                    group="primaza.io",
                    version="v1alpha1",
                    namespace="primaza-system",
                    plural="clusterenvironments",
                    name=ce_name).get("status", {}).get("state", None),
                check_success=lambda x: x is not None and x == state,
                step=5,
                timeout=timeout)
        except polling2.TimeoutException:
            ce_status = cobj.get_namespaced_custom_object_status(
                group="primaza.io",
                version="v1alpha1",
                namespace="primaza-system",
                plural="clusterenvironments",
                name=ce_name)
            logger.log_error("Timed out waiting for cluster environment "
                             f"{ce_name}. State was {state}")
            logger.log_error(f"environment: \n{yaml.dump(ce_status)}")
            raise RuntimeError("[ERROR] Timed out waiting for cluster "
                               f"environment: {ce_name} state: {state}")

    def check_status_condition(self, ce_name: str, ctype: str, cstatus: str):
        logger.log_entry(f"check status condition, ce_name: {ce_name},"
                         f"type: {ctype}, status {cstatus}")
        api_client = self.kube_config_wrapper.get_api_client()
        cobj = client.CustomObjectsApi(api_client)

        ce_status = cobj.get_namespaced_custom_object_status(
            group="primaza.io",
            version="v1alpha1",
            namespace="primaza-system",
            plural="clusterenvironments",
            name=ce_name)
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

    def uninstall_primaza(self):
        out, err = self.kubectl_do(f"delete -f {self.primaza_config}")
        print(out)

        if err != 0:
            raise RuntimeError(
                "error deleting Primaza's controller from "
                f"cluster {self.cluster_name} : {err}")

    def kubeconfig(self) -> KubeConfigWrapper:
        return KubeConfigWrapper(self.cluster_name, self.kube_config_file)

    def kubectl_do(self, cmd: str) -> Tuple[str, int]:
        return Command().run(
            "kubectl"
            f" --kubeconfig {self.kube_config_file}"
            f" --context {self.cluster_name}"
            f" {cmd}")
