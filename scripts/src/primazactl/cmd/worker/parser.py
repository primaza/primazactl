from primazactl.cmd.worker.join import add_join
from primazactl.cmd.worker.create.namespace import \
    add_create_applications_namespace, \
    add_create_services_namespace


def add_group(subparsers, parents=[]):
    worker_group = subparsers.add_parser(
        name="worker",
        help="Operations on main Worker cluster",
        parents=parents)
    worker_subparsers = worker_group.add_subparsers()

    add_join(worker_subparsers, parents=parents)

    add_create(worker_subparsers, parents=parents)


def add_create(subparsers, parents=[]):
    create_group = subparsers.add_parser(
        name="create",
        help="create namespaces on worker cluster",
        parents=parents)
    worker_subparsers = create_group.add_subparsers()

    add_create_applications_namespace(worker_subparsers, parents=parents)

    add_create_services_namespace(worker_subparsers, parents=parents)
