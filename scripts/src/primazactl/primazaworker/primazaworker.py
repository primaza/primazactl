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
from primazactl.utils import command
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

    def create_primaza_user(self, csr_pem: bytes, csr_name, timeout: int = 60):

        logger.log_entry()
        """
        Creates a CertificateSigningRequest for user primaza, approves it,
        and creates the needed roles and role bindings.
        """
        api_client = self.kube_config_wrapper.get_api_client()

        logger.log_info("call CertificatesV1Api")
        certs = client.CertificatesV1Api(api_client)

        # Check if CertificateSigningRequest has yet been created and approved
        logger.log_info(f"Check if CertificateSigningRequest {csr_name} "
                        "has already been created and approved")
        try:
            s = certs.read_certificate_signing_request_status(name=csr_name)
            if s == "Approved":
                logger.log_info(f"cluster '{self.cluster_name}' already has "
                                "an approved CertificateSigningRequest "
                                f"'{csr_name}'")
                return
        except ApiException as e:
            if e.reason != "Not Found":
                raise e

        # Create CertificateSigningRequest
        logger.log_info(f"Create CertificateSigningRequest: {csr_name}")
        v1csr = client.V1CertificateSigningRequest(
            metadata=client.V1ObjectMeta(name=csr_name),
            spec=client.V1CertificateSigningRequestSpec(
                signer_name="kubernetes.io/kube-apiserver-client",
                request=base64.b64encode(csr_pem).decode("utf-8"),
                expiration_seconds=86400,
                usages=["client auth"]))
        certs.create_certificate_signing_request(v1csr)

        # Approve CertificateSigningRequest
        logger.log_info("Approve CertificateSigningRequest")
        v1csr = certs.read_certificate_signing_request(name=csr_name)
        approval_condition = client.V1CertificateSigningRequestCondition(
            last_update_time=datetime.now(timezone.utc).astimezone(),
            message='This certificate was approved by primazactl',
            reason='primazactl worker install',
            type='Approved',
            status='True')
        v1csr.status.conditions = [approval_condition]
        # Approve CertificateSigningRequest
        certs.replace_certificate_signing_request_approval(name=csr_name,
                                                           body=v1csr)
        logger.log_info("Configure primaza user permissions")
        # Configure primaza user permissions
        self.__configure_primaza_user_permissions()

        # Wait for certificate emission
        logger.log_info("Wait for certificate emission")
        tend = datetime.now() + timedelta(seconds=timeout)
        while datetime.now() < tend:
            v1csr = certs.read_certificate_signing_request(name=csr_name)
            status = v1csr.status
            if hasattr(status, 'certificate') \
                    and status.certificate is not None:
                logger.log_info(f"CertificateSignignRequest '{csr_name}' "
                                f"certificate is ready!")
                self.certificate = status.certificate
                return
            logger.log_info(f"CertificateSignignRequest '{csr_name}' "
                            f"certificate is not ready")
            time.sleep(5)

        msg = "Timed-out waiting CertificateSignignRequest " \
              f"'{csr_name}' certificate to become ready"
        logger.log_error(msg)
        raise RuntimeError(msg)

    def __configure_primaza_user_permissions(self):

        logger.log_entry()
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
                client.V1PolicyRule(
                    api_groups=[""],
                    resources=["secrets"],
                    verbs=["create"]),
                client.V1PolicyRule(
                    api_groups=["primaza.io/v1alpha1"],
                    resources=["servicebindings"],
                    verbs=["create"]),
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

    def get_csr_kubeconfig(self, certificate_key: str, csr_name: str) -> Dict:
        """
        Generates the kubeconfig for the CertificateSignignRequest `csr`.
        The key used when creating the CSR is also needed.
        """
        logger.log_entry(f"csr name: {csr_name}")

        kcw = self.kube_config_wrapper.get_kube_config_for_cluster()
        kcd = kcw.get_kube_config_content_as_yaml()
        key_data = base64.b64encode(certificate_key.encode("utf-8")).\
            decode("utf-8")
        kcd["contexts"][0]["context"]["user"] = csr_name
        kcd["users"][0]["name"] = csr_name
        kcd["users"][0]["user"]["client-key-data"] = key_data
        kcd["users"][0]["user"]["client-certificate-data"] = self.certificate
        if self.cluster_name != self.primaza_main.cluster_name:
            new_url = self.get_updated_server_url()
            if new_url:
                kcd["clusters"][0]["cluster"]["server"] = new_url

        logger.log_info(f"csr kubeconfig:\n{yaml.dump(kcd)}")

        return yaml.dump(kcd)

    def get_updated_server_url(self):

        logger.log_entry()
        cluster = f'{self.cluster_name.replace("kind-","")}'
        control_plane = f'{cluster}-control-plane'
        out, err = command.Command().run(f"docker inspect {control_plane}")
        if err != 0:
            raise RuntimeError("\n[ERROR] error getting data from docker:"
                               f"{self.cluster_name}-control-plane : {err}")

        docker_data = yaml.safe_load(out)
        try:
            networks = docker_data[0]["NetworkSettings"]["Networks"]
            ipaddr = networks["kind"]["IPAddress"]
            logger.log_info(f"new worker url: https://{ipaddr}:6443")
            return f"https://{ipaddr}:6443"
        except KeyError:
            logger.log_info("new worker url not found")
            return ""

    def install_worker(self):

        logger.log_entry()
        # need an agnostic way to get the kubeconfig - get as a parameter

        api_client = self.kube_config_wrapper.get_api_client()
        corev1 = client.CoreV1Api(api_client)
        api_response = corev1.list_namespace()
        for item in api_response.items:
            print(f"Namespace: {item.metadata.name} is {item.status.phase}")

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
        csr_name = "primaza"
        p_csr_pem = self.primaza_main.create_certificate_signing_request_pem()
        self.create_primaza_user(p_csr_pem, csr_name)

        logger.log_info("Create cluster context secret in main")
        secret_name = f"primaza-{self.cluster_environment}-kubeconfig"
        cc_kubeconfig = self.get_csr_kubeconfig(
            self.primaza_main.certificate_private_key, csr_name)
        self.primaza_main.create_clustercontext_secret(
            secret_name, cc_kubeconfig)

        logger.log_info("Create cluster environment in main")
        self.primaza_main.write_cluster_environment(self.cluster_environment,
                                                    self.environment,
                                                    secret_name)

        self.primaza_main.check_state(self.cluster_environment,
                                      "Online")
        self.primaza_main.check_status_condition(self.cluster_environment,
                                                 "Online", "True")
        self.primaza_main.\
            check_status_condition(self.cluster_environment,
                                   "ApplicationNamespacePermissionsRequired",
                                   "False")
        self.primaza_main.\
            check_status_condition(self.cluster_environment,
                                   "ServiceNamespacePermissionsRequired",
                                   "False")

        logger.log_exit("Worker install complete")

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
