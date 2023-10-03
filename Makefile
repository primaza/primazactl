# VERSION defines the project version for the bundle.
# Update this value when you upgrade the version of your project.
# To re-generate a bundle for another specific version without changing the standard setup, you can:
# - use the VERSION as arg of the bundle target (e.g make bundle VERSION=0.0.2)
# - use environment variables to overwrite this value (e.g export VERSION=0.0.2)
VERSION ?= latest
PRIMAZA_CTL_VERSION ?= $(shell git describe --tags --always --abbrev=8 --dirty)

# Setting SHELL to bash allows bash commands to be executed by recipes.
# Options are set to exit when a recipe line exits non-zero or a piped command fails.
SHELL = /usr/bin/env bash -o pipefail
.SHELLFLAGS = -ec

# SET RUN_FROM to config the create config files or release to use a release
RUN_FROM ?= config
GIT_ORG ?= primaza
IMG = ghcr.io/$(GIT_ORG)/primaza:$(VERSION)
IMG_APP = ghcr.io/$(GIT_ORG)/primaza-agentapp:$(VERSION)
IMG_SVC = ghcr.io/$(GIT_ORG)/primaza-agentsvc:$(VERSION)
IMG_APP_LOCAL = agentapp:$(VERSION)
IMG_SVC_LOCAL = agentsvc:$(VERSION)

# set CLEAN to "clusters" to only refresh clusters
CLEAN ?= all

PROJECT_DIR := $(shell dirname $(abspath $(lastword $(MAKEFILE_LIST))))

PRIMAZA_REPO = https://github.com/primaza/primaza.git
PRIMAZA_BRANCH ?= main

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
KUSTOMIZE_VERSION ?= v4.5.7
CONTROLLER_TOOLS_VERSION ?= v0.11.3

PYTHON_VENV_DIR ?= $(OUTPUT_DIR)/venv3
HACK_DIR ?= $(PROJECT_DIR)/hack
SCRIPTS_DIR = $(PROJECT_DIR)/scripts
TEMP_DIR = $(OUTPUT_DIR)/temp

PRIMAZA_CONFIG_DIR ?= $(OUTPUT_DIR)/config
$(PRIMAZA_CONFIG_DIR):
	mkdir -p $(PRIMAZA_CONFIG_DIR)

APPLICATION_NAMESPACE ?= primaza-application
SERVICE_NAMESPACE ?= primaza-service
SERVICE_ACCOUNT_NAMESPACE ?= worker-sa

PRIMAZA_CONFIG_FILE ?= $(PRIMAZA_CONFIG_DIR)/control_plane_config_$(VERSION).yaml
WORKER_CONFIG_FILE ?= $(PRIMAZA_CONFIG_DIR)/crds_config_$(VERSION).yaml
APPLICATION_AGENT_CONFIG_FILE ?= $(PRIMAZA_CONFIG_DIR)/application_namespace_config_$(VERSION).yaml
SERVICE_AGENT_CONFIG_FILE ?= $(PRIMAZA_CONFIG_DIR)/service_namespace_config_$(VERSION).yaml

KIND_CONFIG_DIR ?= $(SCRIPTS_DIR)/src/primazatest/config
TENANT_KIND_CONFIG_FILE ?= $(KIND_CONFIG_DIR)/kind-main.yaml
JOIN_KIND_CONFIG_FILE ?= $(KIND_CONFIG_DIR)/kind-worker.yaml
KIND_CLUSTER_TENANT_NAME ?= primazactl-tenant-test
KUBE_KIND_CLUSTER_TENANT_NAME ?= kind-$(KIND_CLUSTER_TENANT_NAME)
KIND_CLUSTER_JOIN_NAME ?= primazactl-join-test
KUBE_KIND_CLUSTER_JOIN_NAME ?= kind-$(KIND_CLUSTER_JOIN_NAME)

KEY_FILE_NAME ?= primaza_private.key
KEY_FILE_DIR ?= $(OUTPUT_DIR)/keys
KEY_FILE =  $(KEY_FILE_DIR)/$(KEY_FILE_NAME)

VERSION_FILE = $(SCRIPTS_DIR)/src/primazactl/version.py

OPTIONS_FILE = $(SCRIPTS_DIR)/src/primazatest/options/primaza-alice.yaml

KUSTOMIZE_INSTALL_SCRIPT ?= "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh"
.PHONY: kustomize
kustomize: $(KUSTOMIZE) ## Download kustomize locally if necessary.
$(KUSTOMIZE): $(LOCALBIN)
	test -s $(LOCALBIN)/kustomize || { curl -Ss $(KUSTOMIZE_INSTALL_SCRIPT) | bash -s -- $(subst v,,$(KUSTOMIZE_VERSION)) $(LOCALBIN); }

.PHONY: manifests
manifests: clone ## Generate WebhookConfiguration, ClusterRole and CustomResourceDefinition objects.
	cd $(TEMP_DIR) && make manifests

.PHONY: config
config: clone manifests kustomize $(PRIMAZA_CONFIG_DIR) application_agent_config service_agent_config ## Get config files from primaza repo.
	-rm $(PRIMAZA_CONFIG_FILE)
	-rm $(WORKER_CONFIG_FILE)
	cd $(TEMP_DIR)/config/manager && $(KUSTOMIZE) edit set image primaza-controller=$(IMG)
	cd $(TEMP_DIR)/config/manager && \
		$(KUSTOMIZE) edit add configmap manager-config \
			--behavior merge --disableNameSuffixHash \
			--from-literal agentapp-image=$(IMG_APP) \
			--from-literal agentsvc-image=$(IMG_SVC)
	$(KUSTOMIZE) build $(TEMP_DIR)/config/default > $(PRIMAZA_CONFIG_FILE)
	$(KUSTOMIZE) build $(TEMP_DIR)/config/crd > $(WORKER_CONFIG_FILE)

.PHONY: application_agent_config
application_agent_config: clone
	-rm $(APPLICATION_AGENT_CONFIG_FILE)
	$(KUSTOMIZE) build --load-restrictor LoadRestrictionsNone $(TEMP_DIR)/config/agents/app/namespace > $(APPLICATION_AGENT_CONFIG_FILE)

.PHONY: service_agent_config
service_agent_config: clone
	-rm $(SERVICE_AGENT_CONFIG_FILE)
	$(KUSTOMIZE) build --load-restrictor LoadRestrictionsNone $(TEMP_DIR)/config/agents/svc/namespace > $(SERVICE_AGENT_CONFIG_FILE)

.PHONY: image
image:
	docker pull $(IMG)
	docker pull $(IMG_APP)
	docker tag $(IMG_APP) $(IMG_APP_LOCAL)
	docker pull $(IMG_SVC)
	docker tag $(IMG_SVC) $(IMG_SVC_LOCAL)

.PHONY: kind-clusters
kind-clusters: image
ifeq ($(CLEAN),all)
	$(MAKE) image
endif
	-kind delete cluster --name $(KIND_CLUSTER_TENANT_NAME)
	-kind delete cluster --name $(KIND_CLUSTER_JOIN_NAME)
	kind create cluster --config $(TENANT_KIND_CONFIG_FILE) --name $(KIND_CLUSTER_TENANT_NAME) && kubectl wait --for condition=Ready nodes --all --timeout=600s
	kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.9.1/cert-manager.yaml
	kubectl rollout status -n cert-manager deploy/cert-manager-webhook -w --timeout=120s
	kind load docker-image $(IMG) --name $(KIND_CLUSTER_TENANT_NAME)
	kind create cluster --config $(JOIN_KIND_CONFIG_FILE) --name $(KIND_CLUSTER_JOIN_NAME) && kubectl wait --for condition=Ready nodes --all --timeout=600s
	kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.9.1/cert-manager.yaml
	kubectl rollout status -n cert-manager deploy/cert-manager-webhook -w --timeout=120s
	kind load docker-image $(IMG_APP_LOCAL) --name $(KIND_CLUSTER_JOIN_NAME)
	kind load docker-image $(IMG_SVC_LOCAL) --name $(KIND_CLUSTER_JOIN_NAME)

.PHONY: setup-test
setup-test: clean kind-clusters
ifeq ($(CLEAN),all)
	$(MAKE) primazactl
endif
ifeq ($(RUN_FROM),config)
	$(MAKE) config
endif

.PHONY: clone
clone: clean-temp
	git clone $(PRIMAZA_REPO) $(TEMP_DIR)
	cd $(TEMP_DIR) && git checkout $(PRIMAZA_BRANCH)

.PHONY: primazactl
primazactl: ## Setup virtual environment
	echo '__version__ = "$(PRIMAZA_CTL_VERSION)"' > $(VERSION_FILE)
	echo '__primaza_version__ = "$(VERSION)"' >> $(VERSION_FILE)
	-rm -rf $(PYTHON_VENV_DIR)
	python3 -m venv $(PYTHON_VENV_DIR)
	$(PYTHON_VENV_DIR)/bin/pip install --upgrade setuptools
	$(PYTHON_VENV_DIR)/bin/pip install --upgrade pip
	cd $(SCRIPTS_DIR) && $(PYTHON_VENV_DIR)/bin/pip3 install -r requirements.txt
	cd $(SCRIPTS_DIR) && $(PYTHON_VENV_DIR)/bin/python3 setup.py install
	source $(PYTHON_VENV_DIR)/bin/activate

.PHONY: single-binary
single-binary: ## Release primazactl as single binary
	echo '__version__ = "$(PRIMAZA_CTL_VERSION)"' > $(VERSION_FILE)
	echo '__primaza_version__ = "$(VERSION)"' >> $(VERSION_FILE)
	-rm -rf $(PYTHON_VENV_DIR)
	python3 -m venv $(PYTHON_VENV_DIR)
	$(PYTHON_VENV_DIR)/bin/pip3 install --upgrade pyinstaller
	$(PYTHON_VENV_DIR)/bin/pip3 install -r $(SCRIPTS_DIR)/requirements.txt
	$(PYTHON_VENV_DIR)/bin/pyinstaller \
		--onefile \
		--clean \
		--noconfirm \
		--path $(SCRIPTS_DIR)/src \
		--distpath $(PYTHON_VENV_DIR)/dist \
		--workpath $(PYTHON_VENV_DIR)/build \
		$(SCRIPTS_DIR)/src/primazactl/primazactl.py

.PHONY: lint
lint: primazactl ## Check python code
	PYTHON_VENV_DIR=$(PYTHON_VENV_DIR) $(HACK_DIR)/check-python/lint-python-code.sh

.PHONY: test-local
test-local: setup-test
ifeq ($(RUN_FROM),config)
	$(PYTHON_VENV_DIR)/bin/primazatest -p $(PYTHON_VENV_DIR) -e $(WORKER_CONFIG_FILE) -f $(PRIMAZA_CONFIG_FILE) -c $(KUBE_KIND_CLUSTER_JOIN_NAME) -m $(KUBE_KIND_CLUSTER_TENANT_NAME) -a $(APPLICATION_AGENT_CONFIG_FILE) -s $(SERVICE_AGENT_CONFIG_FILE) -j $(SERVICE_ACCOUNT_NAMESPACE)
else
	$(PYTHON_VENV_DIR)/bin/primazatest -p $(PYTHON_VENV_DIR) -c $(KUBE_KIND_CLUSTER_JOIN_NAME) -m $(KUBE_KIND_CLUSTER_TENANT_NAME) -j $(SERVICE_ACCOUNT_NAMESPACE) -v $(VERSION) -g $(GIT_ORG)
endif

.PHONY: test-version
test-version: setup-test
	$(PYTHON_VENV_DIR)/bin/primazatest -p $(PYTHON_VENV_DIR) -c $(KUBE_KIND_CLUSTER_JOIN_NAME) -m $(KUBE_KIND_CLUSTER_TENANT_NAME) -v $(VERSION) -g $(GIT_ORG)

.PHONY: test-released
test-released:
	make kind-clusters
	$(PYTHON_VENV_DIR)/bin/primazatest -p $(PYTHON_VENV_DIR) -v $(VERSION) -c $(KUBE_KIND_CLUSTER_JOIN_NAME) -m $(KUBE_KIND_CLUSTER_TENANT_NAME)  -g $(GIT_ORG)

.PHONY: test-users
test-users: setup-test create-users
ifeq ($(RUN_FROM),config)
	$(PYTHON_VENV_DIR)/bin/primazatest -u -i $(OUTPUT_DIR)/users -p $(PYTHON_VENV_DIR) -e $(WORKER_CONFIG_FILE) -f $(PRIMAZA_CONFIG_FILE) -c $(KUBE_KIND_CLUSTER_JOIN_NAME) -m $(KUBE_KIND_CLUSTER_TENANT_NAME) -a $(APPLICATION_AGENT_CONFIG_FILE) -s $(SERVICE_AGENT_CONFIG_FILE)
else
	$(PYTHON_VENV_DIR)/bin/primazatest -u -i $(OUTPUT_DIR)/users -p $(PYTHON_VENV_DIR) -c $(KUBE_KIND_CLUSTER_JOIN_NAME) -m $(KUBE_KIND_CLUSTER_TENANT_NAME) -v $(VERSION) -g $(GIT_ORG)
endif

.PHONY: test-dry-run
test-dry-run: setup-test
ifeq ($(RUN_FROM),config)
	$(PYTHON_VENV_DIR)/bin/primazatest -d -p $(PYTHON_VENV_DIR) -e $(WORKER_CONFIG_FILE) -f $(PRIMAZA_CONFIG_FILE) -c $(KUBE_KIND_CLUSTER_JOIN_NAME) -m $(KUBE_KIND_CLUSTER_TENANT_NAME) -a $(APPLICATION_AGENT_CONFIG_FILE) -s $(SERVICE_AGENT_CONFIG_FILE) -t $(OPTIONS_FILE)
else
	$(PYTHON_VENV_DIR)/bin/primazatest -d -p $(PYTHON_VENV_DIR) -c $(KUBE_KIND_CLUSTER_JOIN_NAME) -m $(KUBE_KIND_CLUSTER_TENANT_NAME) -v $(VERSION) -t $(OPTIONS_FILE) -g $(GIT_ORG)
endif

.PHONY test-local-no-setup:
ifeq ($(RUN_FROM),config)
	$(PYTHON_VENV_DIR)/bin/primazatest -p $(PYTHON_VENV_DIR) -e $(WORKER_CONFIG_FILE) -f $(PRIMAZA_CONFIG_FILE) -c $(KUBE_KIND_CLUSTER_JOIN_NAME) -m $(KUBE_KIND_CLUSTER_TENANT_NAME) -a $(APPLICATION_AGENT_CONFIG_FILE) -s $(SERVICE_AGENT_CONFIG_FILE)
else
	$(PYTHON_VENV_DIR)/bin/primazatest -p $(PYTHON_VENV_DIR) -c $(KUBE_KIND_CLUSTER_JOIN_NAME) -m $(KUBE_KIND_CLUSTER_TENANT_NAME) -v $(VERSION) -g $(GIT_ORG)
endif

.PHONY: test-output
test-output: setup-test
ifeq ($(RUN_FROM),config)
	$(PYTHON_VENV_DIR)/bin/primazatest -o -p $(PYTHON_VENV_DIR) -e $(WORKER_CONFIG_FILE) -f $(PRIMAZA_CONFIG_FILE) -c $(KUBE_KIND_CLUSTER_JOIN_NAME) -m $(KUBE_KIND_CLUSTER_TENANT_NAME) -a $(APPLICATION_AGENT_CONFIG_FILE) -s $(SERVICE_AGENT_CONFIG_FILE)
else
	$(PYTHON_VENV_DIR)/bin/primazatest -o -p $(PYTHON_VENV_DIR) -c $(KUBE_KIND_CLUSTER_JOIN_NAME) -m $(KUBE_KIND_CLUSTER_TENANT_NAME) -v $(VERSION) -g $(GIT_ORG)
endif

.PHONY: test-apply
test-apply: setup-test
	$(PYTHON_VENV_DIR)/bin/primazatest -t $(OPTIONS_FILE) -p $(PYTHON_VENV_DIR) -v $(VERSION)  -g $(GIT_ORG)

.PHONY: create-users
create-users: primazactl
	-rm -rf $(OUTPUT_DIR)/users
	$(PYTHON_VENV_DIR)/bin/primazauser tenant -c $(KUBE_KIND_CLUSTER_TENANT_NAME) -o $(OUTPUT_DIR)/users
	$(PYTHON_VENV_DIR)/bin/primazauser tenant-bad -c $(KUBE_KIND_CLUSTER_TENANT_NAME) -o $(OUTPUT_DIR)/users
	$(PYTHON_VENV_DIR)/bin/primazauser worker -c $(KUBE_KIND_CLUSTER_JOIN_NAME) -o $(OUTPUT_DIR)/users
	$(PYTHON_VENV_DIR)/bin/primazauser worker-bad -c $(KUBE_KIND_CLUSTER_JOIN_NAME) -o $(OUTPUT_DIR)/users
	$(PYTHON_VENV_DIR)/bin/primazauser application-agent -c $(KUBE_KIND_CLUSTER_JOIN_NAME) -o $(OUTPUT_DIR)/users
	$(PYTHON_VENV_DIR)/bin/primazauser application-agent-bad -c $(KUBE_KIND_CLUSTER_JOIN_NAME) -o $(OUTPUT_DIR)/users
	$(PYTHON_VENV_DIR)/bin/primazauser service-agent -c $(KUBE_KIND_CLUSTER_JOIN_NAME) -o $(OUTPUT_DIR)/users
	$(PYTHON_VENV_DIR)/bin/primazauser service-agent-bad -c $(KUBE_KIND_CLUSTER_JOIN_NAME) -o $(OUTPUT_DIR)/users

.PHONY: test
test: setup-test test-local test-released

.PHONY: clean
clean:
ifeq ($(CLEAN),clusters)
	$(MAKE) delete-clusters
else
	$(MAKE) clean-all
endif

.PHONY: clean-temp
clean-temp:
	-chmod 755 $(TEMP_DIR)/bin/k8s/*
	-rm -rf $(TEMP_DIR)

.PHONY: clean-all
clean-all: clean-temp delete-clusters
	-rm -rf $(OUTPUT_DIR)
	-rm -rf $(SCRIPTS_DIR)/build
	-rm -rf $(SCRIPTS_DIR)/dist
	-rm -rf $(SCRIPTS_DIR)/src/rh_primaza_control.egg-info
	-rm -rf $(LOCALBIN)
	-docker image rm $(IMG_APP_LOCAL)
	-docker image rm $(IMG_SVC_LOCAL)

.PHONY: delete-clusters
delete-clusters:
	-kind delete cluster --name $(KIND_CLUSTER_TENANT_NAME)
	-kind delete cluster --name $(KIND_CLUSTER_JOIN_NAME)
