import os
from pathlib import Path


def from_env() -> str:
    return os.environ.get(
            "KUBECONFIG",
            os.path.join(Path.home(), ".kube", "config"))
