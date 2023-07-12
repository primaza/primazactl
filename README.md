# Table of Contents
 - [Introduction](#introduction)
 - [Building the tool ](#building-the-tool)
 - [Running the tool](#running-the-tool)
   - [Pre-reqs](#pre-reqs)
   - [Help](#help)  
   - [Command summary](#command-summary)
   - [create tenant](#create-tenant-command) 
     - [Help](#create-tenant-help)
     - [Options](#create-tenant-options)
   - [delete tenant](#delete-tenant-command)
     - [Help](#delete-tenant-help)
     - [Options](#delete-tenant-options)     
    - [join cluster](#join-cluster-command)
     - [Help](#join-cluster-help)
     - [Options](#join-cluster-options)
    - [create application-namespace](#create-application-namespace-command)
      - [Help](#create-application-namespace-help) 
      - [Options](#create-application-namespace-options)
    - [create service-namespace](#create-service-namespace-command)
        - [Help](#create-service-namespace-help)
        - [Options](#create-service-namespace-options)
 - [Testing](#testing) 


# Introduction

`primazactl` is a simple Command Line Application for Primaza Administrators.

The current implementation provides:
- [Create tenant](#create-tenant-command).
- [Delete tenant](#delete-tenant-command).  
- [Join cluster](#join-cluster-command).
- [Create service-namespace](#create-service-namespace-command).
- [Create application-namespace](#create-application-namespace-command).

For information about primaza see: [Primaza readme](https://github.com/primaza/primaza#readme)


# Building the tool
 
1. Clone this repository
1. Run: `make primazactl`
1. Tool will be available in `out/venv3/bin/primazactl`
1. For example, from the repository root directory:
  - `out/venv3/bin/primazactl create tenant primaza-system`

# Running the tool

## Pre-reqs:
- python
- kubectl installed and a kube-apiserver available.
    - see: [kubernetes documentation](https://kubernetes.io/docs/home/)
- docker    
- a cluster for the tenant and a cluster to join to the tenant.
  - get two kind clusters by running `make kind-cluster`.
    - tenant cluster:
        - default cluster name is primazactl-tenant-test.
        - set environment variable `KIND_CLUSTER_TENANT_NAME` to overwrite.
        - the configuration file used when creating the cluster is `scripts/src/primazatest/config/kind-main.yaml`. 
        - set environment variable `TENANAT_KIND_CONFIG_FILE` to overwrite.
    - join cluster:
        - default cluster name is primazactl-join-test.
        - set environment variable `KIND_CLUSTER_JOIN_NAME` to overwrite.
        - the configuration file used when creating the cluster is `scripts/src/primazatest/config/kind-worker.yaml`.
        - set environment variable `JOIN_KIND_CONFIG_FILE` to overwrite.
    - For information on kind see : (kind quick start)[https://kind.sigs.k8s.io/docs/user/quick-start/].
- a certificate manager available in the cluster on which primaza tenant will be installed.
  - `make kind cluster` installs a certificate manager.

## GitHub Authentication

Some commands may need to use GitHub's API, e.g. to fetch Primaza's manifests.
GitHub's limits for anonymous calls to its API is very strict.
To increase the limit, you need to authenticate.
`primazactl` can authorize requests by fetching the `GITHUB_TOKEN` environment variable and using its content to authenticate with GitHub.
The `GITHUB_TOKEN` environment variable needs to contain a valid [GitHub Personal Access Token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens).

## Help

Primazactl help is organized in a hierarchy with contextual help available for different commands:
- `primazactl --help`
- `primazactl create --help`
- `primazactl create tenant --help`
- `primazactl delete --help`
- `primazactl delete tenant --help`
- `primazactl join --help`
- `primazactl join cluster --help`
- `primazactl create application-namespace --help`
- `primazactl create service-namespace --help`

## Command Summary

- Create tenant
  - checks user has the permissions required to run the command.
    - if not, create tenant is not performed, and a message is output with details of missing permissions.
  - creates a specified namespace, default is `primaza-system`.
    - control-plane `primaza-controller-manager`
    - default image installed: `ghcr.io/primaza/primaza:latest`
  - adds kubernetes resources required by primaza tenant.
- Join cluster
    - requires tenant to be created first.
    - checks user has the permissions required to run the command.
      - if not, join cluster is not performed, and a message is output with details of missing permissions.
    - add kubernetes resources required to join a cluster.
    - creates an [identity](docs/identities.md#identities) which is shared with the primaza tenant.   
    - creates a cluster-environment resource in primaza tenant to enable communication with the joined cluster.
- Create application-namespace.
    - requires join cluster to be complete first.
    - checks user has the permissions required to run the command.
        - if not, create application-namespace is not performed, and a message is output with details of missing permissions.
    - creates a specified namespace, default is `primaza-application`.
    - creates an [identity](docs/identities.md#identities) in the primaza tenant namespace which is shared with the application namespace.
        - enables primaza tenant to access the namespace
    - creates a service account for the application-namespace to access kubernetes resources.
    - provides join cluster primaza service account with access to the namespace
- Create service-namespace.
    - requires join cluster to be complete first.
    - checks user has the permissions required to run the command.
        - if not, create service-namespace is not performed, and a message is output with details of missing permissions.
    - creates a specified namespace, default is `primaza-service`.
    - creates an [identity](docs/identities.md#identities) in the primaza tenant namespace which is shared with the service namespace.
        - enables primaza tenant to access the namespace
    - creates two service accounts for the service-namespace to access kubernetes resources based on two different roles.
    - provides join cluster service account with access to the namespace
    
## Create tenant command

### Create tenant help
```
usage: primazactl create tenant [-h] [-x] [-y {client,server,none}] [-o {yaml,none}] [-f CONFIG] [-v VERSION] [-c CONTEXT] [-k KUBECONFIG] [tenant]

positional arguments:
  tenant                tenant to create. Default: primaza-system

options:
  -h, --help            show this help message and exit
  -x, --verbose         Set for verbose output
  -y {client,server,none}, --dry-run {client,server,none}
                        Set for dry run (default: none)
  -o {yaml,none}, --output {yaml,none}
                        Set to get output of resources which are created (default: none).
  -f CONFIG, --config CONFIG
                        primaza config file. Takes precedence over --version
  -v VERSION, --version VERSION
                        Version of primaza to use, default: latest. Ignored if --config is set.
  -c CONTEXT, --context CONTEXT
                        name of cluster, as it appears in kubeconfig, on which to create the tenant, default: current kubeconfig context
  -k KUBECONFIG, --kubeconfig KUBECONFIG
                        path to kubeconfig file, default: KUBECONFIG environment variable if set, otherwise /<home directory>/.kube/config
```
### Create tenant options
 - `--config CONFIG`:
    - CONFIG: the manifest file for installing primaza main
    - To generate a suitable manifest file:
      - Run `make config` from the repository
      - The manifest will be created: `out/config/primaza_config_latest.yaml`
      - The manifest file sets the namespace to `primaza-system`
      - The manifest file sets the image to `ghcr.io/primaza/primaza:latest`
          - Set the environment variable `IMG` before running make to overwrite the image used.
 - `--context CONTEXT`:
    - CONTEXT: the cluster, as it appears in kubeconfig, on which to install primaza tenant.
    - To create a kind cluster to use for testing:
        - Run `make kind-cluster` 
            - The cluster created for main install is `primazactl-tenant-test`
            - Set the environment variable `KIND_CLUSTER_TENANT_NAME` before running make to overwrite the name of the cluster created.
    - If using kind, prepend `kind-` to the cluster name.
 - `--kubeconfig KUBECONFIG` 
    - The kubeconfig file is not modified by primazactl.
    - The cluster specified for main install does not have to be the current context.
    - Default: KUBECONFIG environment variable if set, otherwise /<home directory>/.kube/config
 - `--version VERSION`
    - Specify the version of manifests to use.
        - see: [releases](https://github.com/primaza/primazactl/releases) for available versions.    
        - Ignored if a config file is set.
        - defaults to the version used to build primazactl.
 - `--output yaml`
    - Outputs the manifests of the resources that are created.
    - The content will be as used for creating the resource.
    - Use with `--dry-run client` to get output without creating resources.
    - Default is `none` - no output is produced.
 - `--dry-run {server,client,none}`
    - If set to `server` 
        - Resources will be created with dry-run and will not be persisted.
        - Output provides the outcome for each resource created.
    - If set to `client`
        - No output produced.
        - Use in conjunction with `--output--` to get output without creating resources.
    - Default: none - resources are persisted.
    
## Delete tenant command

### Delete tenant help
```
usage: primazactl delete tenant [-h] [-x] [-f CONFIG] [-v VERSION] [-c CONTEXT] [-k KUBECONFIG]

options:
  -h, --help            show this help message and exit
  -x, --verbose         Set for verbose output
  -f CONFIG, --config CONFIG
                        primaza config file. Takes precedence over --version
  -v VERSION, --version VERSION
                        Version of primaza to use, default: latest. Ignored if --config is set.
  -c CONTEXT, --context CONTEXT
                        name of cluster, as it appears in kubeconfig, on which primaza tenant was created, default: current kubeconfig context
  -k KUBECONFIG, --kubeconfig KUBECONFIG
                        path to kubeconfig file, default: KUBECONFIG environment variable if set, otherwise /<home directory>/.kube/config
```

### Delete tenant options

see: [Create tenant options](#create-tenant-options).


## Join cluster command

Notes:
- requires a primaza tenant.
- the namespace created is named `kube-system`.
  - Not currently supported to use a different name.


### Join cluster help
```
usage: primazactl join cluster [-h] [-x] [-y {client,server,none}] [-o {yaml,none}] [-f CONFIG] [-v VERSION] [-c CONTEXT] [-k KUBECONFIG] -d
                               CLUSTER_ENVIRONMENT -e ENVIRONMENT [-l TENANT_KUBECONFIG] [-m TENANT_CONTEXT] [-t TENANT]

options:
  -h, --help            show this help message and exit
  -x, --verbose         Set for verbose output
  -y {client,server,none}, --dry-run {client,server,none}
                        Set for dry run (default: none)
  -o {yaml,none}, --output {yaml,none}
                        Set to get output of resources which are created (default: none).
  -f CONFIG, --config CONFIG
                        primaza config file. Takes precedence over --version
  -v VERSION, --version VERSION
                        Version of primaza to use, default: latest. Ignored if --config is set.
  -c CONTEXT, --context CONTEXT
                        name of cluster, as it appears in kubeconfig, to join, default: current kubeconfig context
  -k KUBECONFIG, --kubeconfig KUBECONFIG
                        path to kubeconfig file, default: KUBECONFIG environment variable if set, otherwise /<home directory>/.kube/config
  -d CLUSTER_ENVIRONMENT, --cluster-environment CLUSTER_ENVIRONMENT
                        name to use for the ClusterEnvironment that will be created in Primaza
  -e ENVIRONMENT, --environment ENVIRONMENT
                        the Environment that will be associated to the ClusterEnvironment
  -l TENANT_KUBECONFIG, --tenant-kubeconfig TENANT_KUBECONFIG
                        path to kubeconfig file for the tenant, default: KUBECONFIG environment variable if set, otherwise
                        /<home directory>/.kube/config
  -m TENANT_CONTEXT, --tenant-context TENANT_CONTEXT
                        name of cluster, as it appears in kubeconfig, on which primaza tenant was created. Default: current kubeconfig context
  -t TENANT, --tenant TENANT
                        tenant to use for join. Default: primaza-system
```

### Join cluster options
- `--config CONFIG`:
    - CONFIG contains the manifest file for the join cluster.
    - To generate a suitable manifest file:
        - Run `make config` from the repository
        - The manifest will be created: `out/config/worker_config_latest.yaml` 
- `--context CONTEXT`: 
    - CONTEXT: the cluster, as it appears in kubeconfig, of the join cluster.
    - To create a kind cluster to use for testing:
        - Run `make kind-cluster`
            - The cluster created for the worker is `primazactl-join-test`
            - Set the environment variable `KIND_CLUSTER_JOIN_NAME` before running make to overwrite the name of the cluster created.
    - If using kind, prepend `kind-` to the cluster name.
    - Can use the same cluster as used for main install.
- `--kubeconfig KUBECONFIG`
    - The kubeconfig file is not modified by primazactl.
    - The cluster specified for worker join does not have to be the current context.
    - Default: KUBECONFIG environment variable if set, otherwise /<home directory>/.kube/config
- `--version VERSION`
    - Specify the version of manifests to use.
        - see: [releases](https://github.com/primaza/primazactl/releases) for available versions.
        - Ignored if a config file is set.
        - defaults to the version used to build primazactl.
- `--cluster-environment CLUSTER_ENVIRONMENT`
    - name to be used for the cluster environment resource created in the primaza-main namespace.
- `--environment ENVIRONMENT`
    - the name that will be associated to the ClusterEnvironment,
- `--tenant-kubeconfig TENANT_KUBECONFIG`
    - path to kubeconfig file for the tenant
    - default: KUBECONFIG environment variable if set, otherwise
      /<home directory>/.kube/config
- `--tenant-context TENANT_CONTEXT`
    - only set if cluster on which primaza tenant is installed is different from the one set using the `--context` option.
- `--tenant tenant`
    - Tenant used for the join.
    - Default is `primaza-system`.
- `--output yaml`
    - Outputs the manifests of the resources that are created.
    - The content will be as used for creating the resource.
    - Use with `--dry-run client` to get output without creating resources.
    - Default is `none` - no output is produced.
- `--dry-run {server,client,none}`
    - If set to `server`
        - Resources will be created with dry-run and will not be persisted.
        - Output provides the outcome for each resource created.
    - If set to `client`
        - No output produced.
        - Use in conjunction with `--output--` to get output without creating resources.
    - Default: none - resources are persisted.
    

## Create application namespace command

Notes:
- requires join cluster to be completed.

### Create application-namespace help
```
usage: primazactl create application-namespace [-h] [-x] [-y {client,server,none}] [-o {yaml,none}] -d CLUSTER_ENVIRONMENT [-c CONTEXT]
                                               [-m TENANT_CONTEXT] [-f CONFIG] [-t TENANT] [-v VERSION] [-k KUBECONFIG] [-l TENANT_KUBECONFIG]
                                               namespace

positional arguments:
  namespace             namespace to create

options:
  -h, --help            show this help message and exit
  -x, --verbose         Set for verbose output
  -y {client,server,none}, --dry-run {client,server,none}
                        Set for dry run (default: none)
  -o {yaml,none}, --output {yaml,none}
                        Set to get output of resources which are created (default: none).
  -d CLUSTER_ENVIRONMENT, --cluster-environment CLUSTER_ENVIRONMENT
                        name to use for the ClusterEnvironment that will be created in Primaza
  -c CONTEXT, --context CONTEXT
                        name of cluster, as it appears in kubeconfig, on which to create the service or application namespace, default: current
                        kubeconfig context
  -m TENANT_CONTEXT, --tenant-context TENANT_CONTEXT
                        name of cluster, as it appears in kubeconfig, on which Primaza tenant was created. Default: current kubeconfig context
  -f CONFIG, --config CONFIG
                        Config file containing agent roles
  -t TENANT, --tenant TENANT
                        tenant to use. Default: primaza-system
  -v VERSION, --version VERSION
                        Version of primaza to use, default: latest. Ignored if --config is set.
  -k KUBECONFIG, --kubeconfig KUBECONFIG
                        path to kubeconfig file, default: KUBECONFIG environment variable if set, otherwise /<home directory>/.kube/config
  -l TENANT_KUBECONFIG, --tenant-kubeconfig TENANT_KUBECONFIG
                        path to kubeconfig file for the tenant, default: KUBECONFIG environment variable if set, otherwise
                        /<home directory>/.kube/config                      
```

### Create application-namespace options: 
#### positional arguments:
- `namespace`
    - Namespace to use for application agent.
#### options:
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
- `--tenant TENANT`
     - tenant to use.
     - Default is `primaza-system`.
- `--version VERSION`
    - Specify the version of manifests to use.
        - see: [releases](https://github.com/primaza/primazactl/releases) for available versions.
        - Ignored if a config file is set.
        - Default is the version used to build primazactl.
- `--kubeconfig KUBECONFIG`
    - The kubeconfig file is not modified by primazactl.
    - The cluster specified for worker join does not have to be the current context. 
    - default: KUBECONFIG environment variable if set, otherwise
      /<home directory>/.kube/config
- `--tenant-kubeconfig TENANT_KUBECONFIG`
    - path to kubeconfig file for the tenant 
    - default: KUBECONFIG environment variable if set, otherwise
      /<home directory>/.kube/config
- `--output yaml`
    - Outputs the manifests of the resources that are created.
    - The content will be as used for creating the resource.
    - Use with `--dry-run client` to get output without creating resources.
    - Default is `none` - no output is produced.
- `--dry-run {server,client,none}`
    - If set to `server`
        - Resources will be created with dry-run and will not be persisted.
        - Output provides the outcome for each resource created.
    - If set to `client`
        - No output produced.
        - Use in conjunction with `--output--` to get output without creating resources.
    - Default: none - resources are persisted.

    

## Create service namespace command

Notes:
- requires join cluster to be completed.

    
### Create service-namespace help:
```
usage: primazactl create service-namespace [-h] [-x] [-y {client,server,none}] [-o {yaml,none}] -d CLUSTER_ENVIRONMENT [-c CONTEXT] [-m TENANT_CONTEXT]
                                           [-f CONFIG] [-t TENANT] [-v VERSION] [-k KUBECONFIG] [-l TENANT_KUBECONFIG]
                                           namespace

positional arguments:
  namespace             namespace to create

options:
  -h, --help            show this help message and exit
  -x, --verbose         Set for verbose output
  -y {client,server,none}, --dry-run {client,server,none}
                        Set for dry run (default: none)
  -o {yaml,none}, --output {yaml,none}
                        Set to get output of resources which are created (default: none).




  -d CLUSTER_ENVIRONMENT, --cluster-environment CLUSTER_ENVIRONMENT
                        name to use for the ClusterEnvironment that will be created in Primaza
  -c CONTEXT, --context CONTEXT
                        name of cluster, as it appears in kubeconfig, on which to create the service or application namespace, default: current
                        kubeconfig context
  -m TENANT_CONTEXT, --tenant-context TENANT_CONTEXT
                        name of cluster, as it appears in kubeconfig, on which Primaza tenant was created. Default: current kubeconfig context
  -f CONFIG, --config CONFIG
                        Config file containing agent roles
  -t TENANT, --tenant TENANT
                        tenant to use. Default: primaza-system
  -v VERSION, --version VERSION
                        Version of primaza to use, default: latest. Ignored if --config is set.
  -k KUBECONFIG, --kubeconfig KUBECONFIG
                        path to kubeconfig file, default: KUBECONFIG environment variable if set, otherwise /<home directory>/.kube/config
  -l TENANT_KUBECONFIG, --tenant-kubeconfig TENANT_KUBECONFIG
                        path to kubeconfig file for the tenant, default: KUBECONFIG environment variable if set, otherwise
                        /<home directory>/.kube/config                                                                                              
```

### Create service-namespace options: 
#### positional arguments:
- `namespace`
    - Namespace to use for service agent.
#### options:
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
- `--main-namespace MAIN_NAMESPACE`
    - Namespace of primaza-main.
    - Default is `primaza-system`.
- `--version VERSION`
    - Specify the version of manifests to use.
        - see: [releases](https://github.com/primaza/primazactl/releases) for available versions.
        - Ignored if a config file is set.
        - Defaults to the version used to build primazactl.
- `--kubeconfig KUBECONFIG`
    - The kubeconfig file is not modified by primazactl.
    - The cluster specified for worker join does not have to be the current context.
- `--tenant-kubeconfig TENANT_KUBECONFIG`
  path to kubeconfig file for the tenant, default: KUBECONFIG environment variable if set, otherwise
  /<home directory>/.kube/config
- `--output yaml`
    - Outputs the manifests of the resources that are created.
    - The content will be as used for creating the resource.
    - Use with `--dry-run client` to get output without creating resources.
    - Default is `none` - no output is produced.
- `--dry-run {server,client,none}`
    - If set to `server`
        - Resources will be created with dry-run and will not be persisted.
        - Output provides the outcome for each resource created.
    - If set to `client`
        - No output produced.
        - Use in conjunction with `--output--` to get output without creating resources.
    - Default: none - resources are persisted.

    
# Testing

- To run the basic tests run `make test-local`
  - This will:
    - run `make setup-test`
    - run the test:  `out/venv3/bin/primazatest`
        - src script is `scripts/src/promazatest/runtest.sh`
        - requires inputs: python virtual environment directory, the primaza configuration file and the cluster names.
- To run the test with users run `make test-users` 
    - This will:
    - run `make setup-test`
    - run `make create-users`  
    - run the test:  `out/venv3/bin/primazatest -u`
        - src script is `scripts/src/primazatest/runtest.sh`
        - requires inputs: python virtual environment directory, the primaza configuration file and the cluster names.
- To run the test for dry-run run `make test-dry-run`
  - This will:
  - run `make setup-test`
  - run the test:  `out/venv3/bin/primazatest -d`
      - src script is `scripts/src/primazatest/runtest.sh`
      - requires inputs: python virtual environment directory, the primaza configuration file and the cluster names.
- To run the test for output of resources `make test-output`
    - This will:
    - run `make setup-test`
    - run the test:  `out/venv3/bin/primazatest -o`
        - src script is `scripts/src/primazatest/runtest.sh`
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
    
