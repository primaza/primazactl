# Table of Contents
 - [Introduction](#introduction)
 - [Tool options](#tool-options)
 - [Building the tool ](#building-the-tool)
 - [Running the tool](#running-the-tool)
   - [Pre-reqs](#pre-reqs)
   - [Command options](#command-options)
     - [Positional paramters](#positional-parameters)
     - [Flags](#flags)
 - [Testing](#testing) 
 - [Other useful make targets](#other-useful-make-targets)

# Introduction
```primazactl``` is a simple Command Line Application for Primaza Administrators.

The first implementation includes primaza main install only and more functions will be added over time.

# Tool options

```
usage: primaza [-h] [-f PRIMAZA_CONFIG] [-c CLUSTER_NAME] [-k KUBECONFIG] [-v PRIMAZA_VERSION]
               {install,info,uninstall,join} {main,worker}

Configure and install primaza and primaza worker on clusters

positional arguments:
  {install,info,uninstall,join}
                        type of action to perform.
  {main,worker}         specify primaza or worker.

options:
  -h, --help            show this help message and exit
  -c CLUSTER_NAME, --clustername CLUSTER_NAME
                        name of cluster, as it appears in kubeconfig, on which to install primaza or worker, default:
                        current kubeconfig context
  -k KUBECONFIG, --kubeconfig KUBECONFIG
                        path to kubeconfig file, default: KUBECONFIG environment variable if set, otherwise
                        <home directory>/.kube/config
  -f PRIMAZA_CONFIG, --config PRIMAZA_CONFIG
                        primaza config file. Takes precedence over --version                 
  -v PRIMAZA_VERSION, --version PRIMAZA_VERSION
                        Version of primaza to use, default: newest release available. Ignored if --config is set.
```

# Building the tool
 
1. Clone this repository
1. Run: `make primazactl`
1. Tool will be available in ```out/venv3/bin/primazactl```
1. For example, from repository root directory:
  - ```out/venv3/bin/primazactl install main -f primaza-config.yaml```

# Running the tool

## Pre-reqs:
- python
- kubectl installed and a kube-apiserver available.
    - see: [kubernetes documentation](https://kubernetes.io/docs/home/)
- a cluster available for primaza to be installed.
  - for a kind cluster run `make kind-cluster`.
    - default cluster name is primazactl-test.
      - set environment variable ```KIND_CLUSTER_NAME``` to overwrite.
    - the configuration file used when creating the cluster is ```scripts/src/primazatest/config/kind.yaml```. 
      - set environment variable ```KIND_CONFIG_FILE``` to overwrite.
    - For information on kind see : (kind quick start)[https://kind.sigs.k8s.io/docs/user/quick-start/].
  
## Command options:

### Positional parameters
- {install, info, uninstall, join}
  - The action to perform 
  - Currently, only install is available.
  - Others action are illustrations, may change and will currently be ignored.
- {main, worker}
  - The primaza entity on which to perform the action.
  - Currently, only main is available.
  - worker is an illustration, may change and will currently be ignored.

### Flags
- All flags are optional.
- ```-f```, ```--config--```
  - a single file with the configuration information for primaza main install.
  - to create one based on the main branch of the primaza repository:
    - ```make config```
      - config file is written to ```scripts/config/primaza_config_latest.yaml```
      - default image is: ```quay.io/mmulholl/primaza-main-controllers:latest```
        - set the environment variable ```IMG``` to overwrite the image used.
- ```-c```, ```--clustername--``` 
  - name of cluster on which to install primaza.
  - will default to the cluster which is the current context of kubeconfig.
  - note if using kind, prepend ```kind-``` to the cluster name as provided to kind.
    - for example for ```kind create cluster primaza-test``` the cluster specified to primazactl is ```kind-primaza-cluster```.
- ```-k```, ```--kubeconfig``` 
  - path of kubeconfig file to use.
    - first default is ```KUBECONFIG``` environment variable.
    - second default is ```<HOME>/.kube/config```
- ```-v``` , ```--version```
    - the version of the image to install.
    - must be a semantic version.  
    - will be an alternative to the config file when supported.
      - once a release is created in this repo which contains a primaza config file named ```primaza_config_{release.tag_name}.yaml```.
    - not currently available for use.
    - the future plan is for a default version to be used when neither config or version are provided. 
  
# Testing

- To run the tests run ```make test```
  - This will combine:
      - ```make clean```
      - ```kind-cluster```
        - Create a kind cluster 
        - default cluster name is primazactl-test
          - set environment variable ```KIND_CLUSTER_NAME``` to overwrite.
        - the configuration file used when creating the cluster is ```scripts/src/primazatest/config/kind.yaml```.
          - set environment variable ```KIND_CONFIG_FILE``` to overwrite.
      - ```make primazactl```
        - creates a python virtual environment from which primazactl can be invoked.
        - default directory is ```out/venv1```
          - set environment variable ```PYTHON_VENV_DIR``` to overwrite.
      - ```make config```
        - Creates a primaza configuration file.
          - clones the primaza repository.
          - uses kustomize to create a single config file from ```config/default```
          - image is set by default to ```quay.io/mmulholla/primaza-main-controllers:latest```
            - set the environment variable ```IMG``` overwrite the image used.
      - runs the test:  ```out/venv3/bin/primazatest```
        - src script is ```scripts/src/promazatest/runtest.sh```
          - requires inputs: python virtual environment directory, the primaza configuration file and the cluster name.
        
# Other useful make targets:

  - ```lint```
    - run lint on the python files.
  - ```primaza-main-controllers```
    - clones the primaza repository and runs 
      - make primaza docker-build
      - make primaza docker-push
      - image is set by default to ```quay.io/mmulholla/primaza-main-controllers:latest```
        - set the environment variable ```IMG``` overwrite the image used.
        - to push to ```quay.io``` you will need to run ```docker login quay.io```
