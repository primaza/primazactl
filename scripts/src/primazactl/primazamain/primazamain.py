import tempfile
from primazactl.utils import command
from primazactl.utils import kubeconfigwrapper
from primazactl.utils import primazaconfig


class PrimazaMain(object):

    kube_config_file: str = None
    cluster_name: str = None
    kustomize: str = None
    primaza_config: str = None
    primaza_version: str = None

    def __init__(self, cluster_name: str, kubeconfigfile: str,
                 config: str, version: str):
        self.cluster_name = cluster_name
        self.kube_config_file = kubeconfigfile
        self.primaza_config = config
        self.primaza_version = version

    def start(self):
        self.install_primaza()

    def install_primaza(self):

        img = "primaza-controller:latest"

        # need an agnostic way to get the kubeconfig - get as a parameter
        kcw = kubeconfigwrapper.KubeConfigWrapper(self.cluster_name,
                                                  self.kube_config_file)
        kcc = kcw.get_kube_config_content()
        with tempfile.NamedTemporaryFile(
                prefix=f"kubeconfig-primaza-{self.cluster_name}-") \
                as t:
            t.write(kcc.encode("utf-8"))
            self.__deploy_primaza(t.name, img)

    def __deploy_primaza(self, kubeconfig_path: str, img: str):

        # make sure we deploy to the required cluster
        kc = kubeconfigwrapper.KubeConfigWrapper(self.cluster_name,
                                                 kubeconfig_path)
        kc.use_context()

        print(f"self.primaza_config = {self.primaza_config}")
        if self.primaza_config:
            print(f"self.primaza_config = {self.primaza_config}")
            out, err = command.Command().setenv("KUBECONFIG", kubeconfig_path)\
                .run(f"kubectl apply -f {self.primaza_config}")
        else:
            config = primazaconfig.PrimazaConfig(self.primaza_version).\
                      get_config()
            with tempfile.NamedTemporaryFile(
                    prefix=f"kubeconfig-primaza-{self.cluster_name}-") \
                    as t:
                t.write(config.encode("utf-8"))
                out, err = command.Command().\
                    setenv("KUBECONFIG", kubeconfig_path).\
                    run(f"kubectl apply -f {t.name}")

        print(out)
        if err != 0:
            raise RuntimeError("\n[ERROR] error deploying "
                               "Primaza's controller into "
                               f"cluster {self.cluster_name} : {err}\n")
