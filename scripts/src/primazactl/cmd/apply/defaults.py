from primazactl.primazamain.constants import DEFAULT_TENANT
from primazactl.version import __primaza_version__
from primazactl.utils.kubeconfig import from_env
from primazactl.primazaworker.constants import WORKER_NAMESPACE


defaults = {"apiVersion": "primaza.io/v1alpha1",
            "kind": "Tenant",
            "tenant": DEFAULT_TENANT,
            "version": __primaza_version__,
            "kubeconfig": from_env(),
            "tenant_config": "control_plane_config_latest.yaml",
            "worker_config": "crds_config_latest.yaml",
            "service_agent_config": "service_namespace_config_latest.yaml",
            "app_agent_config": "application_namespace_config_latest.yaml",
            "service_account_namespace": WORKER_NAMESPACE}
