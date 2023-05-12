from primazactl.cmd.delete.tenant.parser import add_delete_tenant


def add_group(subparsers, parents=[]):
    main_group = subparsers.add_parser(
        name="delete",
        help="Delete a Primaza resource",
        parents=parents)
    main_subparsers = main_group.add_subparsers()
    add_delete_tenant(main_subparsers, parents=parents)
