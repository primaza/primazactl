# VERSION defines the project version for the bundle.
# Update this value when you upgrade the version of your project.
# To re-generate a bundle for another specific version without changing the standard setup, you can:
# - use the VERSION as arg of the bundle target (e.g make bundle VERSION=0.0.2)
# - use environment variables to overwrite this value (e.g export VERSION=0.0.2)
VERSION ?= 0.0.1

# Setting SHELL to bash allows bash commands to be executed by recipes.
# Options are set to exit when a recipe line exits non-zero or a piped command fails.
SHELL = /usr/bin/env bash -o pipefail
.SHELLFLAGS = -ec

IMG ?= quay.io/mmulholl/primaza-main-controllers:latest
#

IMG ?= controller:latest
PROJECT_DIR := $(shell dirname $(abspath $(lastword $(MAKEFILE_LIST))))

PRIMAZA_REPO = https://github.com/primaza/primaza.git
PRIMAZA_BRANCH = main

.PHONY: all
all: lint test

##@ General

# The help target prints out all targets with their descriptions organized
# beneath their categories. The categories are represented by '##@' and the
# target descriptions by '##'. The awk commands is responsible for reading the
# entire set of makefiles included in this invocation, looking for lines of the
# file as xyz: ## something, and then pretty-format the target and help. Then,
# if there's a line with ##@ something, that gets pretty-printed as a category.
# More info on the usage of ANSI control characters for terminal formatting:
# https://en.wikipedia.org/wiki/ANSI_escape_code#SGR_parameters
# More info on the awk command:
# http://linuxcommand.org/lc3_adv_awk.php

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Development


ifndef ignore-not-found
  ignore-not-found = false
endif

##@ Build Dependencies


## Location to install dependencies to

OUTPUT_DIR ?= $(PROJECT_DIR)/out
$(OUTPUT_DIR):
	mkdir -p $(OUTPUT_DIR)

LOCALBIN ?= $(OUTPUT_DIR)/bin
$(LOCALBIN):
	mkdir -p $(LOCALBIN)

GOCACHE ?= "$(OUTPUT_DIR)/.gocache"
GOFLAGS ?=
GO ?= GOCACHE=$(GOCACHE) GOFLAGS="$(GOFLAGS)" go

## Tool Binaries
KUSTOMIZE ?= $(LOCALBIN)/kustomize
CONTROLLER_GEN ?= $(LOCALBIN)/controller-gen

## Tool Versions
KUSTOMIZE_VERSION ?= v5.0.0
CONTROLLER_TOOLS_VERSION ?= v0.11.3

PYTHON_VENV_DIR ?= $(OUTPUT_DIR)/venv3
HACK_DIR ?= $(PROJECT_DIR)/hack
SCRIPTS_DIR = $(PROJECT_DIR)/scripts
TEMP_DIR = $(OUTPUT_DIR)/temp

PRIMAZA_CONFIG_DIR ?= $(OUTPUT_DIR)/config
$(PRIMAZA_CONFIG_DIR):
	mkdir -p $(PRIMAZA_CONFIG_DIR)

PRIMAZA_CONFIG_FILE = $(PRIMAZA_CONFIG_DIR)/primaza_config_latest.yaml
WORKER_CONFIG_FILE = $(PRIMAZA_CONFIG_DIR)/worker_config_latest.yaml

KIND_CONFIG_DIR ?= $(SCRIPTS_DIR)/src/primazatest/config
MAIN_KIND_CONFIG_FILE ?= $(KIND_CONFIG_DIR)/kind-main.yaml
WORKER_KIND_CONFIG_FILE ?= $(KIND_CONFIG_DIR)/kind-worker.yaml
KIND_CLUSTER_MAIN_NAME ?= primazactl-main-test
KUBE_KIND_CLUSTER_MAIN_NAME ?= kind-$(KIND_CLUSTER_MAIN_NAME)
KIND_CLUSTER_WORKER_NAME ?= primazactl-worker-test
KUBE_KIND_CLUSTER_WORKER_NAME ?= kind-$(KIND_CLUSTER_WORKER_NAME)

KEY_FILE_NAME ?= primaza_private.key
KEY_FILE_DIR ?= $(OUTPUT_DIR)/keys
KEY_FILE =  $(KEY_FILE_DIR)/$(KEY_FILE_NAME)

KUSTOMIZE_INSTALL_SCRIPT ?= "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh"
.PHONY: kustomize
kustomize: $(KUSTOMIZE) ## Download kustomize locally if necessary.
$(KUSTOMIZE): $(LOCALBIN)
	test -s $(LOCALBIN)/kustomize || { curl -Ss $(KUSTOMIZE_INSTALL_SCRIPT) | bash -s -- $(subst v,,$(KUSTOMIZE_VERSION)) $(LOCALBIN); }

.PHONY: controller-gen
controller-gen: clone $(CONTROLLER_GEN) ## Download controller-gen locally if necessary.
$(CONTROLLER_GEN): $(LOCALBIN)
	test -s $(LOCALBIN)/controller-gen || GOBIN=$(LOCALBIN) $(GO) install sigs.k8s.io/controller-tools/cmd/controller-gen@$(CONTROLLER_TOOLS_VERSION)

.PHONY: manifests
manifests: clone controller-gen ## Generate WebhookConfiguration, ClusterRole and CustomResourceDefinition objects.
	cd $(TEMP_DIR) && $(CONTROLLER_GEN) rbac:roleName=manager-role crd webhook paths="./..." output:crd:artifacts:config=config/crd/bases

.PHONY: config
config: clone manifests kustomize $(PRIMAZA_CONFIG_DIR) ## Get config files from primaza repo.
	-rm $(PRIMAZA_CONFIG_FILE)
	cd $(TEMP_DIR)/config/manager && $(KUSTOMIZE) edit set image controller=$(IMG)
	$(KUSTOMIZE) build $(TEMP_DIR)/config/default > $(PRIMAZA_CONFIG_FILE)
	$(KUSTOMIZE) build $(TEMP_DIR)/config/crd > $(WORKER_CONFIG_FILE)

.PHONY: image
image:
	docker pull $(IMG)

.PHONY: kind-clusters
kind-clusters: config image
	-kind delete cluster --name $(KIND_CLUSTER_MAIN_NAME)
	-kind delete cluster --name $(KIND_CLUSTER_WORKER_NAME)
	kind create cluster --config $(MAIN_KIND_CONFIG_FILE) --name $(KIND_CLUSTER_MAIN_NAME) && kubectl wait --for condition=Ready nodes --all --timeout=600s
	kind load docker-image $(IMG) --name $(KIND_CLUSTER_MAIN_NAME)
	kind create cluster --config $(WORKER_KIND_CONFIG_FILE) --name $(KIND_CLUSTER_WORKER_NAME) && kubectl wait --for condition=Ready nodes --all --timeout=600s


.PHONY: setup-test
setup-test: clean image kind-clusters primazactl config create-key


.PHONY: clone
clone: clean-temp
	git clone $(PRIMAZA_REPO) $(TEMP_DIR)
	cd $(TEMP_DIR) && git checkout $(PRIMAZA_BRANCH)

.PHONY: primazactl
primazactl: ## Setup virtual environment
	-rm -rf $(PYTHON_VENV_DIR)
	python3 -m venv $(PYTHON_VENV_DIR)
	$(PYTHON_VENV_DIR)/bin/pip install --upgrade setuptools
	$(PYTHON_VENV_DIR)/bin/pip install --upgrade pip
	cd $(SCRIPTS_DIR) && $(PYTHON_VENV_DIR)/bin/pip3 install -r requirements.txt
	cd $(SCRIPTS_DIR) && $(PYTHON_VENV_DIR)/bin/python3 setup.py install

.PHONY: single-binary
single-binary: ## Release primazactl as single binary
	-rm -rf $(PYTHON_VENV_DIR)
	python3 -m venv $(PYTHON_VENV_DIR)
	$(PYTHON_VENV_DIR)/bin/pip3 install --upgrade pyinstaller
	$(PYTHON_VENV_DIR)/bin/pip3 install -r $(SCRIPTS_DIR)/requirements.txt
	$(PYTHON_VENV_DIR)/bin/pyinstaller \
		--onefile \
		--clean \
		--noconfirm \
		--distpath $(PYTHON_VENV_DIR)/dist \
		--workpath $(PYTHON_VENV_DIR)/build \
		$(SCRIPTS_DIR)/src/primazactl/primazactl.py

.PHONY: lint
lint: primazactl ## Check python code
	PYTHON_VENV_DIR=$(PYTHON_VENV_DIR) $(HACK_DIR)/check-python/lint-python-code.sh

.PHONY: create-key
create-key: primazactl
	-rm -f $(KEY_FILE)
	$(PYTHON_VENV_DIR)/bin/rsakey $(KEY_FILE)

.PHONY: test
test: setup-test
	$(PYTHON_VENV_DIR)/bin/primazatest -v $(PYTHON_VENV_DIR) -e $(WORKER_CONFIG_FILE) -f $(PRIMAZA_CONFIG_FILE) -c $(KUBE_KIND_CLUSTER_WORKER_NAME) -m $(KUBE_KIND_CLUSTER_MAIN_NAME)

.PHONY: clean-temp
clean-temp:
	-chmod 755 $(TEMP_DIR)/bin/k8s/*
	rm -rf $(TEMP_DIR)

.PHONY: clean
clean: clean-temp
	rm -rf $(OUTPUT_DIR)
	rm -rf $(SCRIPTS_DIR)/build
	rm -rf $(SCRIPTS_DIR)/dist
	rm -rf $(SCRIPTS_DIR)/src/rh_primaza_control.egg-info
	rm -rf $(LOCALBIN)
	-kind delete cluster --name $(KIND_CLUSTER_MAIN_NAME)
	-kind delete cluster --name $(KIND_CLUSTER_WORKER_NAME)
