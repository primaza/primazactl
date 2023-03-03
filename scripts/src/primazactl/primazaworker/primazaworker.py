import base64
import time
import yaml
from typing import Dict
from datetime import datetime, timezone, timedelta
from kubernetes import client
from kubernetes.client.rest import ApiException
from primazactl.utils import kubeconfigwrapper
from primazactl.utils import primazaconfig
from primazactl.utils import logger
from primazactl.primazamain import primazamain


class PrimazaWorker(object):

    namespace: str = None
    cluster_name: str = None
    kube_config_file: str = None
    kube_config_wrapper: kubeconfigwrapper.KubeConfigWrapper = None
    config_file: str = None
    version: str = None
    environment: str = None
    cluster_environment: str = None
    primaza_main: primazamain.PrimazaMain = None
    certificate: str = None

    def __init__(self, primaza_main: primazamain.PrimazaMain,
                 cluster_name: str,
                 kube_config_file: str,
                 config_file: str,
                 version: str,
                 environment: str,
                 cluster_environment: str,
                 namespace: str = "primaza-system"):
        self.cluster_name = cluster_name
        self.config_file = config_file
        kcw = kubeconfigwrapper.KubeConfigWrapper(cluster_name,
                                                  kube_config_file)
        self.kube_config_wrapper = kcw.get_kube_config_for_cluster()
        self.version = version
        self.environment = environment
        self.cluster_environment = cluster_environment
        self.namespace = namespace
        self.primaza_main = primaza_main
        logger.log_info("PrimazaWorker created for cluster "
                        f"{self.cluster_name}")

    def create_primaza_user(self, csr_pem: bytes, timeout: int = 60):

        logger.log_entry()
        """
        Creates a CertificateSigningRequest for user primaza, approves it,
        and creates the needed roles and role bindings.
        """
        csr = f"primaza-{self.environment}"
        api_client = self.kube_config_wrapper.get_api_client()

        logger.log_info("call CertificatesV1Api")
        certs = client.CertificatesV1Api(api_client)

        # Check if CertificateSigningRequest has yet been created and approved
        logger.log_info(f"Check if CertificateSigningRequest {csr} "
                        "has already been created and approved")
        try:
            s = certs.read_certificate_signing_request_status(name=csr)
            if s == "Approved":
                logger.log_info(f"cluster '{self.cluster_name}' already has "
                                "an approved CertificateSigningRequest "
                                f"'{csr}'")
                return
        except ApiException as e:
            if e.reason != "Not Found":
                raise e

        # Create CertificateSigningRequest
        logger.log_info(f"Create CertificateSigningRequest: {csr}")
        v1csr = client.V1CertificateSigningRequest(
            metadata=client.V1ObjectMeta(name=csr),
            spec=client.V1CertificateSigningRequestSpec(
                signer_name="kubernetes.io/kube-apiserver-client",
                request=base64.b64encode(csr_pem).decode("utf-8"),
                expiration_seconds=86400,
                usages=["client auth"]))
        certs.create_certificate_signing_request(v1csr)

        # Approve CertificateSigningRequest
        logger.log_info("Approve CertificateSigningRequest")
        v1csr = certs.read_certificate_signing_request(name=csr)
        approval_condition = client.V1CertificateSigningRequestCondition(
            last_update_time=datetime.now(timezone.utc).astimezone(),
            message='This certificate was approved by primazactl',
            reason='primazactl worker install',
            type='Approved',
            status='True')
        v1csr.status.conditions = [approval_condition]
        # Approve CertificateSigningRequest
        certs.replace_certificate_signing_request_approval(name=csr,
                                                           body=v1csr)
        logger.log_info("Configure primaza user permissions")
        # Configure primaza user permissions
        self.__configure_primaza_user_permissions()

        # Wait for certificate emission
        logger.log_info("Wait for certificate emission")
        tend = datetime.now() + timedelta(seconds=timeout)
        while datetime.now() < tend:
            v1csr = certs.read_certificate_signing_request(name=csr)
            status = v1csr.status
            if hasattr(status, 'certificate') \
                    and status.certificate is not None:
                logger.log_info(f"CertificateSignignRequest '{csr}' "
                                f"certificate is ready!")
                self.certificate = status.certificate
                return
            logger.log_info(f"CertificateSignignRequest '{csr}' "
                            f"certificate is not ready")
            time.sleep(5)

        msg = "Timed-out waiting CertificateSignignRequest " \
              f"'{csr}' certificate to become ready"
        logger.log_error(msg)
        raise RuntimeError(msg)

    def __configure_primaza_user_permissions(self):

        logger.log_entry("configure_primaza_user_permissions")
        api_client = self.kube_config_wrapper.get_api_client()
        rbac = client.RbacAuthorizationV1Api(api_client)
        try:
            rbac.read_cluster_role_binding(name="primaza-primaza")
            return
        except ApiException as e:
            if e.reason != "Not Found":
                raise e

        role = client.V1ClusterRole(
            metadata=client.V1ObjectMeta(name="primaza"),
            rules=[
                client.V1PolicyRule(
                    api_groups=[""],
                    resources=["pods"],
                    verbs=["list", "get", "create"]),
            ])
        rbac.create_cluster_role(role)

        role_binding = client.V1ClusterRoleBinding(
            metadata=client.V1ObjectMeta(name="primaza-primaza"),
            role_ref=client.V1RoleRef(api_group="rbac.authorization.k8s.io",
                                      kind="ClusterRole", name="primaza"),
            subjects=[
                client.V1Subject(api_group="rbac.authorization.k8s.io",
                                 kind="User", name="primaza"),
            ])
        rbac.create_cluster_role_binding(role_binding)

    def get_csr_kubeconfig(self, certificate_key: str, csr: str) -> Dict:
        """
        Generates the kubeconfig for the CertificateSignignRequest `csr`.
        The key used when creating the CSR is also needed.
        """
        logger.log_entry()

        kcw = self.kube_config_wrapper.get_kube_config_for_cluster()

        kcd = kcw.get_kube_config_content_as_yaml()
        key_data = base64.b64encode(certificate_key.encode("utf-8")).\
            decode("utf-8")
        kcd["contexts"][0]["context"]["user"] = csr
        kcd["users"][0]["name"] = csr
        kcd["users"][0]["user"]["client-key-data"] = key_data
        kcd["users"][0]["user"]["client-certificate-data"] = "certificate"

        return str(kcd)

    def write_resource(self, resource):
        logger.log_entry()
        resource_config = primazaconfig.PrimazaConfig()
        resource_config.set_content(resource)
        resource_config.apply(self.kube_config_wrapper)

    def write_secret(self, cluster_environment_name):
        logger.log_entry("kind: secret, cluster_environment_name: "
                         f"{cluster_environment_name}")
        resource = {"apiVersion": "v1",
                    "kind": "Secret",
                    "metadata": {
                        "name": f"primaza-{cluster_environment_name}"
                                "-kubeconfig",
                        "namespace": self.namespace
                        },
                    "data": {
                        "kubeconfig": base64.b64encode(
                            self.kube_config_wrapper.
                            get_kube_config_content().
                            encode('utf8')).decode("utf-8")
                        }
                    }

        self.write_resource(yaml.dump(resource))

    def write_cluster_environment(self,
                                  cluster_environment_name,
                                  environment_name):

        logger.log_entry("kind: ClusterEnvironment, "
                         "cluster_environment_name: "
                         f"{cluster_environment_name}"
                         f"environment_name: {environment_name}")

        resource = {"apiVersion": "primaza.io/v1alpha1",
                    "kind": "ClusterEnvironment",
                    "metadata": {
                        "name": cluster_environment_name,
                        "namespace": self.namespace
                    },
                    "spec": {
                        "environmentName": environment_name,
                        "clusterContextSecret": "primaza-"
                                                f"{cluster_environment_name}"
                                                "-kubeconfig"
                    }
                    }

        self.write_resource(yaml.dump(resource))

    def install_worker(self):

        logger.log_entry()
        # need an agnostic way to get the kubeconfig - get as a parameter

        if not self.cluster_name:
            self.cluster_name = self.kube_config_wrapper.get_cluster_name()
            if not self.cluster_name:
                raise RuntimeError("\n[ERROR] installing priamza: "
                                   "no cluster found.")
            else:
                logger.log_info("Cluster set to current context: "
                                f"{self.cluster_name}")

        self.__deploy_worker()

        logger.log_info("Create certificate signing request")
        p_csr_pem = self.primaza_main.create_certificate_signing_request_pem()
        self.create_primaza_user(p_csr_pem)

        logger.log_info("Create cluster context secret in main")
        cc_kubeconfig = self.get_csr_kubeconfig(
            self.primaza_main.certificate_private_key,
            f"primaza-{self.environment}")
        self.primaza_main.create_clustercontext_secret(
            f"primaza-{self.environment}", cc_kubeconfig)

        logger.log_info("Create secret and cluster environment in main")
        self.write_secret(self.cluster_environment)
        self.write_cluster_environment(self.cluster_environment,
                                       self.environment)

        logger.log_exit()

    def __deploy_worker(self):

        logger.log_entry()

        config = primazaconfig.PrimazaConfig("worker",
                                             self.config_file,
                                             self.version)
        logger.log_info("Deploy worker")
        err = config.apply(self.kube_config_wrapper)
        if err != 0:
            raise RuntimeError("\n[ERROR] error deploying "
                               "Primaza's worker into "
                               f"cluster {self.cluster_name} : {err}\n")
