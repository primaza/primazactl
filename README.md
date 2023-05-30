# Table of Contents
 - [Introduction](#introduction)
 - [Building the tool ](#building-the-tool)
 - [Running the tool](#running-the-tool)
   - [Pre-reqs](#pre-reqs)
   - [Help](#help)  
   - [Command summary](#command-summary)
   - [Main install command](#main-install-command)  
     - [Help](#main-install-help)
     - [Options](#main-install-options)
  - [Worker join command](#worker-join-command)
     - [Help](#worker-join-help)
     - [Options](#worker-join-options)
  - [Worker create application namespace command](#worker-create-application-namespace-command)
    - [Help](#worker-create-application-namespace-help)
    - [Options](#worker-create-application-namespace-options)
  - [Worker create service namespace command](#worker-create-service-namespace-command)
    - [Help](#worker-create-service-namespace-help)
    - [Options](#worker-create-service-namespace-options)
 - [Testing](#testing) 


# Introduction

`primazactl` is a simple Command Line Application for Primaza Administrators.

The current implementation provides:
- [main install](#main-install-command) and uninstall.
- [worker join](#worker-install-command).
- [worker create service-namespace](#worker-create-service-namespace-command).
- [worker create application-namespace](#worker-create-application-namespace-command).


# Building the tool
 
1. Clone this repository
1. Run: `make primazactl`
1. Tool will be available in `out/venv3/bin/primazactl`
1. For example, from the repository root directory:
  - `out/venv3/bin/primazactl install main -f primaza-config.yaml`

# Running the tool

## Pre-reqs:
- python
- kubectl installed and a kube-apiserver available.
    - see: [kubernetes documentation](https://kubernetes.io/docs/home/)
- docker    
- a cluster available for primaza to be installed.
  - get a kind cluster by running `make kind-cluster`.
    - default cluster name is primazactl-test.
      - set environment variable `KIND_CONTEXT` to overwrite.
    - the configuration file used when creating the cluster is `scripts/src/primazatest/config/kind.yaml`. 
      - set environment variable `KIND_CONFIG_FILE` to overwrite.
    - For information on kind see : (kind quick start)[https://kind.sigs.k8s.io/docs/user/quick-start/].
- a certificate manager available in the cluster on which primaza main will be installed.
  - `make kind cluster` installs a certificate manager.

## Help

Primazactl help is organized in a hierarchy with contextual help available for different commands:
- `primazactl --help`
- `primazactl main --help`
- `primazactl main install --help`
- `primazactl main uninstall --help`
- `primazactl worker --help`
- `primazactl worker join --help`
- `primazactl worker create --help`
- `primazactl worker create application-namespace --help`
- `primazactl worker create service-namespace --help`

## Command Summary

- Main Install
  - creates a specified namespace, default is `primaza-system`.
    - control-plane `primaza-controller-manager`
    - default image installed: `ghcr.io/primaza/primaza:latest`
  - adds kubernetes resources required by primaza-main  
- Worker Join
    - requires main to be installed first.
    - add kubernetes resources required by primaza-worker
    - creates an [indentity](docs/identities.md#identities) in the worker namespace which is shared with primaza main.   
    - creates a cluster-environment resource in main to enable main-worker communication.
- Worker create application-namespace.
    - requires worker join to be complete first.
    - creates a specified namespace, default is `primaza-application`.
    - creates an [indentity](docs/identities.md#identities) in the main namespace which is shared with the application namespace.
        - enables primaza main to access the namespace
    - creates a service account for the application-namespace to access kubernetes resources.
    - provides primaza worker service account with access to the namespace
- Worker create primaza-service.
    - requires worker join to be complete first.
    - creates a specified namespace, default is `primaza-service`.
    - creates an [indentity](docs/identities.md#identities) in the main namespace which is shared with the service namespace.
        - enables primaza main to access the namespace
    - creates two service accounts for the service-namespace to access kubernetes resources based on two different roles.
    - provides primaza worker service account with access to the namespace
    
## Main install command

### Main install help
```
usage: primazactl main install [-h] [-x] [-f CONFIG] [-v VERSION] [-c CONTEXT] [-k KUBECONFIG] [-n NAMESPACE]

options:
  -h, --help            show this help message and exit
  -x, --verbose         Set for verbose output
  -f CONFIG, --config CONFIG
                        primaza config file. Takes precedence over --version
  -v VERSION, --version VERSION
                        Version of primaza to use. Ignored if --config is set.
  -c CONTEXT, --context CONTEXT
                        name of cluster, as it appears in kubeconfig, on which to install primaza or worker, default: current kubeconfig context
  -k KUBECONFIG, --kubeconfig KUBECONFIG
                        path to kubeconfig file, default: KUBECONFIG environment variable if set, otherwise <USER-HOME>.kube/config
  -n NAMESPACE, --namespace NAMESPACE
                        namespace to use for install. Default: primaza-system

```
### Main install options
 - `--config CONFIG`:
    - CONFIG: the manifest file for installing primaza main
    - To generate a suitable manifest file:
      - Run `make config` from the repository
      - The manifest will be created: `out/config/primaza_config_latest.yaml`
      - The manifest file sets the namespace to `primaza-system`
      - The manifest file sets the image to `ghcr.io/primaza/primaza:latest`
          - Set the environment variable `IMG` before running make to overwrite the image used.
 - `--context CONTEXT`:
    - CONTEXT: the cluster, as it appears in kubeconfig, on which to install primaza main
    - To create a kind cluster to use for testing:
        - Run `make kind-cluster` 
            - The cluster created for main install is `primazactl-main-test`
            - Set the environment variable `KIND_CLUSTER_MAIN_NAME` before running make to overwrite the name of the cluster created.
    - If using kind, prepend `kind-` to the cluster name.
 - `--kubeconfig KUBECONFIG` 
    - The kubeconfig file is not modified by primazactl.
    - The cluster specified for main install does not have to be the current context.
 - `--version VERSION`
    - Specify the version of manifests to use.
        - see: [releases](https://github.com/primaza/primazactl/releases) for available versions.    
        - Ignored if a config file is set.
 - `--namespace NAMESPACE`  
   - Namespace to use for primaza main.
   - Default is `primaza-system`.

## Worker join command

Notes:
- requires primaza main installed.
- the namespace created is named `kube-system`.
  - Not currently supported to use a different name.


### Worker join help
```
usage: primazactl worker join [-h] [-x] [-f CONFIG] [-v VERSION] [-c CONTEXT] [-k KUBECONFIG] -d CLUSTER_ENVIRONMENT -e ENVIRONMENT [-l MAIN_KUBECONFIG] [-m TENANT_CONTEXT]

options:
  -h, --help            show this help message and exit
  -x, --verbose         Set for verbose output
  -f CONFIG, --config CONFIG
                        primaza config file. Takes precedence over --version
  -v VERSION, --version VERSION
                        Version of primaza to use. Ignored if --config is set.
  -c CONTEXT, --context CONTEXT
                        name of cluster, as it appears in kubeconfig, on which to install primaza or worker, default: current kubeconfig context
  -k KUBECONFIG, --kubeconfig KUBECONFIG
                        path to kubeconfig file, default: KUBECONFIG environment variable if set, otherwise /Users/martinmulholland/.kube/config
  -d CLUSTER_ENVIRONMENT, --cluster-environment CLUSTER_ENVIRONMENT
                        name to use for the ClusterEnvironment that will be created in Primaza
  -e ENVIRONMENT, --environment ENVIRONMENT
                        the Environment that will be associated to the ClusterEnvironment
  -l MAIN_KUBECONFIG, --tenant-kubeconfig MAIN_KUBECONFIG
                        path to kubeconfig file, default: KUBECONFIG environment variable if set, otherwise /Users/martinmulholland/.kube/config
  -m TENANT_CONTEXT, --tenant-context TENANT_CONTEXT
                        name of cluster, as it appears in kubeconfig, on which Primaza is installed. Default: current kubeconfig context
  -s MAIN_NAMESPACE, --main-namespace MAIN_NAMESPACE
                        namespace to use for join. Default: primaza-system
```
### Worker join options
- `--config CONFIG`:
    - CONFIG contains the manifest file for the primaza worker.
    - To generate a suitable manifest file:
        - Run `make config` from the repository
        - The manifest will be created: `out/config/worker_config_latest.yaml` 
- `--context CONTEXT` 
    - CONTEXT: the cluster, as it appears in kubeconfig, on which to add primaza-worker
    - To create a kind cluster to use for testing:
        - Run `make kind-cluster`
            - The cluster created for the worker is `primazactl-worker-test`
            - Set the environment variable `KIND_CLUSTER_WORKER_NAME` before running make to overwrite the name of the cluster created.
    - If using kind, prepend `kind-` to the cluster name.
    - Can use the same cluster as used for main install.
- `--kubeconfig KUBECONFIG`
    - The kubeconfig file is not modified by primazactl.
    - The cluster specified for worker join does not have to be the current context.
- `--version VERSION`
    - Specify the version of manifests to use.
        - see: [releases](https://github.com/primaza/primazactl/releases) for available versions.
        - Ignored if a config file is set.
- `--cluster-environment CLUSTER_ENVIRONMENT`
    - name to be used for the cluster environment resource created in the primaza-main namespace.
- `--environment ENVIRONMENT`
    - the name that will be associated to the ClusterEnvironment,
- `--tenant-kubeconfig MAIN_KUBECONFIG`
    - only set if the cluster on which primaza main installed is in a different kubeconfig file from the one set using the `--kubeconfig` option.
- `--tenant-context TENANT_CONTEXT`
    - only set if cluster on which primaza main is installed is different from the one set using the `--context` option.
- `--main-namespace MAIN_NAMESPACE`
    - Namespace of primaza-main.
    - Default is `primaza-system`.
    

## Worker create application namespace command

Notes:
- requires primaza worker join to be completed.

### Worker create application-namespace help
```
usage: primazactl worker create application-namespace [-h] [-x] -d CLUSTER_ENVIRONMENT [-c CONTEXT] [-m TENANT_CONTEXT] [-f CONFIG]

options:
  -h, --help            show this help message and exit
  -x, --verbose         Set for verbose output
  -d CLUSTER_ENVIRONMENT, --cluster-environment CLUSTER_ENVIRONMENT
                        name to use for the ClusterEnvironment that will be created in Primaza
  -c CONTEXT, --context CONTEXT
                        name of worker cluster, as it appears in kubeconfig, on which to create the namespace, default: current kubeconfig context
  -m TENANT_CONTEXT, --tenant-context TENANT_CONTEXT
                        name of cluster, as it appears in kubeconfig, on which Primaza is installed. Default: current kubeconfig context
  -f CONFIG, --config CONFIG
                        Config file containing agent roles
  -n NAMESPACE, --namespace NAMESPACE
                        namespace to create. Default: primaza-application
  -s MAIN_NAMESPACE, --main-namespace MAIN_NAMESPACE
                        namespace of primaza main. Default: primaza-system
  -v VERSION, --version VERSION
                        Version of primaza to use. Ignored if --config is set.                        
```

### Worker create application-namespace options: 
- `--context CONTEXT`
    - CONTEXT: the cluster, as it appears in kubeconfig, on which primaza-worker is installed
- `--cluster-environment CLUSTER_ENVIRONMENT`
    - Used in the name of the primaza main [indentity](docs/identities.md#identities).
- `--tenant-context TENANT_CONTEXT`
    - Name of cluster, as it appears in kubeconfig, on which Primaza main is installed. Default: current kubeconfig context
- `--config CONFIG`
    - Config file containing thr manifests for application agent roles.
    - To generate a suitable config file:
        - Run `make config` from the repository
        - The config will be created: `out/config/application_agent_config_latest.yaml`
- `--namespace NAMESPACE`
    - Namespace to use for application agent.
    - Default is `primaza-application`. 
- `--main-namespace MAIN_NAMESPACE`
     - Namespace of primaza-main.
     - Default is `primaza-system`.
- `--version VERSION`
    - Specify the version of manifests to use.
        - see: [releases](https://github.com/primaza/primazactl/releases) for available versions.
        - Ignored if a config file is set.
    

## Worker create service namespace command

Notes:
- requires primaza worker join to be completed.

    
### Worker create service-namespace help:
```
usage: primazactl worker create service-namespace [-h] [-x] -d CLUSTER_ENVIRONMENT [-c CONTEXT] [-m TENANT_CONTEXT] [-f CONFIG]

options:
  -h, --help            show this help message and exit
  -x, --verbose         Set for verbose output
  -d CLUSTER_ENVIRONMENT, --cluster-environment CLUSTER_ENVIRONMENT
                        name to use for the ClusterEnvironment that will be created in Primaza
  -c CONTEXT, --context CONTEXT
                        name of worker cluster, as it appears in kubeconfig, on which to create the namespace, default: current kubeconfig context
  -m TENANT_CONTEXT, --tenant-context TENANT_CONTEXT
                        name of cluster, as it appears in kubeconfig, on which Primaza is installed. Default: current kubeconfig context
  -f CONFIG, --config CONFIG
                        Config file containing agent roles
  -n NAMESPACE, --namespace NAMESPACE
                        namespace to create. Default: primaza-service
  -s MAIN_NAMESPACE, --main-namespace MAIN_NAMESPACE
                        namespace of primaza main. Default: primaza-system
  -v VERSION, --version VERSION
                        Version of primaza to use. Ignored if --config is set.                                                
```

### Worker create service-namespace options: 
- `--context CONTEXT`
    - CONTEXT: the cluster, as it appears in kubeconfig, on which primaza-worker is installed
- `--cluster-environment CLUSTER_ENVIRONMENT`
    - Used in the name of the primaza main [indentity](docs/identities.md#identities).
- `--tenant-context TENANT_CONTEXT`
    - name of cluster, as it appears in kubeconfig, on which Primaza main is installed. Default: current kubeconfig context
- `--config CONFIG`
    - Config file containing thr manifests for application agent roles.
    - To generate a suitable config file:
        - Run `make config` from the repository
        - The config will be created: `out/config/service_agent_config_latest.yaml`
- `--namespace NAMESPACE`
    - Namespace to use for service agent.
    - Default is `primaza-service`.
- `--main-namespace MAIN_NAMESPACE`
    - Namespace of primaza-main.
    - Default is `primaza-system`.
- `--version VERSION`
    - Specify the version of manifests to use.
        - see: [releases](https://github.com/primaza/primazactl/releases) for available versions.
        - Ignored if a config file is set.    
    
# Testing

- To run the tests run `make test`
  - This will:
    - run `make setup-test`
    - run the test:  `out/venv3/bin/primazatest`
        - src script is `scripts/src/promazatest/runtest.sh`
        - requires inputs: python virtual environment directory, the primaza configuration file and the cluster names.
- To set up the test environment run `make setup-test` 
  - This will run in order:  
      - `make clean`
        - deletes:
          - test clusters, 
          - generated config files. 
          - python virtual environment.
      - `kind-cluster`
        - Creates two kind clusters 
          - `primazactl-main-test`
            - used to install primaza main by the tests
            - set environment variable `KIND_MAIN_CONTEXT` to overwrite. 
            - a configuration file is used when creating the cluster 
               - The file used if `scripts/src/primazatest/config/kind-main.yaml`.
               - set environment variable `MAIN_KIND_CONFIG_FILE` to overwrite.
          - `primazactl-worker-test`
            - used by the tests:
                - worker join.
                - worker create application-namespace.
                - worker create service-namespace.
            - set environment variable `KIND_WORKER_CONTEXT` to overwrite.
            - a configuration file is used when creating the cluster
                - The file used if `scripts/src/primazatest/config/kind-worker.yaml`.
                - set environment variable `WORKER_KIND_CONFIG_FILE` to overwrite.
     - `make primazactl`
        - creates a python virtual environment from which primazactl can be invoked.
        - default directory is `out/venv1`
          - set environment variable `PYTHON_VENV_DIR` to overwrite.
      - `make config`
        - Creates primaza configuration files required by pimazactl.
          - clones the primaza repository.
          - uses kustomize to create config files:
            - `out/config/primaza_config_latest.yaml`
                - Sets the namespace to `primaza-system`
                - Sets the image to `ghcr.io/primaza/primaza:latest`
                    - Set the environment variable `IMG` before running make to overwrite the image used.
            - `out/config/worker_config_latest.yaml`
            - `out/config/application_agent_config_latest.yaml`
               - namespace is set to `primaza-application`
                   - Set the environment variable `APPLICATION_NAMESPACE` before running make to overwrite the namesapce used.
            - `out/config/service_agent_config_latest.yaml`
                - namespace is set to `primaza-service`
                    - Set the environment variable `SERVICE_NAMESPACE` before running make to overwrite the namesapce used.
    