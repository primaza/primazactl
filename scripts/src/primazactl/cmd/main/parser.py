from primazactl.cmd.main.install import add_install
from primazactl.cmd.main.uninstall import add_uninstall


def add_group(subparsers, parents=[]):
    main_group = subparsers.add_parser(
        name="main",
        help="Operations on main Primaza cluster",
        parents=parents)
    main_subparsers = main_group.add_subparsers()

    add_install(main_subparsers, parents=parents)
    add_uninstall(main_subparsers, parents=parents)
