# Identities

To set up and configure Primaza, `primazactl` creates several identities and shares their credentials across different clusters.
These identities rely on Kubernetes Service Accounts and [Service Account's tokens](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/#manually-create-a-long-lived-api-token-for-a-serviceaccount).

As an example, when primazactl configures a cluster to work with an instance of Primaza, it creates a Service Account and a Service Account's token.
This data is collected and used to build a kubeconfig that, in turn, is shared with Primaza.
Primaza will now use the kubeconfig to connect and authenticate with the worker cluster.

The module [primazactl.identity](../scripts/src/primazactl/identity/) stores the implementation of the Identity concept.
