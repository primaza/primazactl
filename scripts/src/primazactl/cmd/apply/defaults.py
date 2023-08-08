from primazactl.primazamain.constants import DEFAULT_TENANT
from primazactl.version import __primaza_version__
from primazactl.utils.kubeconfig import from_env


defaults = {"apiVersion": "primaza.io/v1alpha1",
            "kind": "Tenant",
            "tenant": DEFAULT_TENANT,
            "version": __primaza_version__,
            "kubeconfig": from_env(),
            "tenant_config": "primaza_config_latest.yaml",
            "worker_config": "worker_config_latest.yaml",
            "service_agent_config": "service_agent_config_latest.yaml",
            "app_agent_config": "application_agent_config_latest.yaml"}
