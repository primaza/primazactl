from primazactl.cmd.create.tenant.parser import add_create_tenant
from primazactl.cmd.create.namespace.application.parser \
        import add_create_application_namespace
from primazactl.cmd.create.namespace.service.parser \
        import add_create_service_namespace


def add_group(subparsers, parents=[]):
    main_group = subparsers.add_parser(
        name="create",
        help="Create a Primaza resource",
        parents=parents)
    main_subparsers = main_group.add_subparsers()
    add_create_tenant(main_subparsers, parents=parents)
    add_create_application_namespace(main_subparsers, parents=parents)
    add_create_service_namespace(main_subparsers, parents=parents)
