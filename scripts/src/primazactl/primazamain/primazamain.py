
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from primazactl.utils import kubeconfigwrapper
from primazactl.utils import primazaconfig
from primazactl.utils import logger
from kubernetes import client
from kubernetes.client.rest import ApiException


class PrimazaMain(object):

    kube_config_wrapper: kubeconfigwrapper.KubeConfigWrapper = None
    cluster_name: str = None
    kustomize: str = None
    primaza_config: str = None
    primaza_version: str = None

    certificate_private_key: bytes = None
    certificate: RSAPrivateKey = None
    primaza_namespace: str = "primaza-system"

    def __init__(self, cluster_name: str, kubeconfigfile: str,
                 config_file: str, version: str,
                 private_key_file: str, namespace: str):
        self.cluster_name = cluster_name
        kcw = kubeconfigwrapper.KubeConfigWrapper(cluster_name,
                                                  kubeconfigfile)
        self.kube_config_wrapper = kcw.get_kube_config_for_cluster()
        self.primaza_config = config_file
        self.primaza_version = version
        if namespace:
            self.primaza_namespace = namespace
        if private_key_file:
            logger.log_info(f"Read the key file : {private_key_file}")
            with open(private_key_file, "rb") as key_file:
                self.certificate = serialization.\
                    load_pem_private_key(key_file.read(), password=None)
        logger.log_info("Primaza main created for cluster "
                        f"{self.cluster_name}")

    def install_primaza(self):
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

        self.__deploy_primaza()

    def __deploy_primaza(self):
        logger.log_entry()

        config = primazaconfig.PrimazaConfig("main", self.primaza_config,
                                             self.primaza_version)
        err = config.apply(self.kube_config_wrapper)
        if err != 0:
            raise RuntimeError("\n[ERROR] error deploying "
                               "Primaza's main controller into "
                               f"cluster {self.cluster_name} : {err}\n")

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
        self.certificate_private_key = self.certificate.private_bytes(
            format=serialization.PrivateFormat.PKCS8,
            encoding=serialization.Encoding.PEM,
            encryption_algorithm=serialization.NoEncryption()).decode("utf-8")

        c = self.__create_certificate_signing_request()
        return c.public_bytes(serialization.Encoding.PEM)

    def create_clustercontext_secret(self, secret_name: str, kubeconfig: str):
        """
        Creates the Primaza's ClusterContext secret
        """
        logger.log_entry()

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

        logger.log_info("create secret")
        secret = client.V1Secret(
            metadata=client.V1ObjectMeta(name=secret_name),
            string_data={"kubeconfig": kubeconfig})

        logger.log_info("create_namespaced_secret")
        corev1.create_namespaced_secret(namespace=self.primaza_namespace,
                                        body=secret)
