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

PROJECT_DIR := $(shell dirname $(abspath $(lastword $(MAKEFILE_LIST))))

PRIMAZA_REPO = https://github.com/primaza/primaza.git
PRIMAZA_BRANCH = main

.PHONY: all
all: kustomize

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
LOCALBIN ?= $(PROJECT_DIR)/scripts/bin
$(LOCALBIN):
	mkdir -p $(LOCALBIN)

## Tool Binaries
KUSTOMIZE ?= $(LOCALBIN)/kustomize

## Tool Versions
KUSTOMIZE_VERSION ?= v5.0.0

OUTPUT_DIR ?= $(PROJECT_DIR)/out
$(OUTPUT_DIR):
	mkdir -p $(OUTPUT_DIR)
PYTHON_VENV_DIR ?= $(OUTPUT_DIR)/venv3
HACK_DIR ?= $(PROJECT_DIR)/hack
SCRIPTS_DIR = $(PROJECT_DIR)/scripts
TEMP_DIR = $(PROJECT_DIR)/temp

PRIMAZA_CONFIG_DIR ?= $(SCRIPTS_DIR)/config
$(PRIMAZA_CONFIG_DIR):
	mkdir -p $(PRIMAZA_CONFIG_DIR)

PRIMAZA_CONFIG_FILE = $(PRIMAZA_CONFIG_DIR)/primaza_config_latest.yaml

KIND_CONFIG_DIR ?= $(SCRIPTS_DIR)/src/primazatest/config
KIND_CONFIG_FILE ?= $(KIND_CONFIG_DIR)/kind.yaml
KIND_CLUSTER_NAME ?= primazactl-test
KUBE_KIND_CLUSTER_NAME ?= kind-$(KIND_CLUSTER_NAME)

KUSTOMIZE_INSTALL_SCRIPT ?= "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh"
.PHONY: kustomize
kustomize: $(KUSTOMIZE) ## Download kustomize locally if necessary.
$(KUSTOMIZE): $(LOCALBIN)
	test -s $(LOCALBIN)/kustomize || { curl -Ss $(KUSTOMIZE_INSTALL_SCRIPT) | bash -s -- $(subst v,,$(KUSTOMIZE_VERSION)) $(LOCALBIN); }

.PHONY: config
config: clone kustomize $(PRIMAZA_CONFIG_DIR) ## Get config files from primaza repo.
	-rm $(PRIMAZA_CONFIG_FILE)
	cd $(TEMP_DIR)/config/manager && $(KUSTOMIZE) edit set image controller=$(IMG)
	$(KUSTOMIZE) build $(TEMP_DIR)/config/default > $(PRIMAZA_CONFIG_FILE)

.PHONY: primaza-main-controllers
primaza-main-controllers: clone
	cd temp && export IMG=$(IMG) && make primaza docker-build
	cd temp && export IMG=$(IMG) && make primaza docker-push

ifeq ($(shell sh -c 'uname 2>/dev/null || echo Unknown'),Darwin)
SED_EXTRA := .bak
endif

.PHONY: kind-cluster
kind-cluster: $(SED-EXTRA)
	-kind delete cluster --name $(KIND_CLUSTER_NAME)
	##kind create cluster --name $(KIND_CLUSTER_NAME) && kubectl wait --for condition=Ready nodes --all --timeout=600s
	sed -i $(SED_EXTRA) 's/name:.*/name: $(KIND_CLUSTER_NAME)/g' $(KIND_CONFIG_FILE)
	kind create cluster --config $(KIND_CONFIG_FILE) && kubectl wait --for condition=Ready nodes --all --timeout=600s

.PHONY: setup-test
setup-test: clean kind-cluster primazactl config

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

.PHONY: lint
lint: primazactl ## Check python code
	PYTHON_VENV_DIR=$(PYTHON_VENV_DIR) $(HACK_DIR)/check-python/lint-python-code.sh

.PHONY: test
test: setup-test
	$(PYTHON_VENV_DIR)/bin/primazatest -v $(PYTHON_VENV_DIR) -f $(PRIMAZA_CONFIG_FILE) -c $(KUBE_KIND_CLUSTER_NAME)

.PHONY: clean-temp
clean-temp:
	-chmod 755 $(TEMP_DIR)/bin/k8s/*
	rm -rf $(TEMP_DIR)

.PHONY: clean
clean: clean-temp
	rm -rf $(OUTPUT_DIR)
	rm -rf $(LOCALBIN)
	rm -rf $(PRIMAZA_CONFIG_DIR)
	-kind delete cluster --name $(KIND_CLUSTER_NAME)
