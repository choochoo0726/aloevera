"""Command-line interface for aloevera."""

import argparse
import sys


def _cmd_export_html(args):
    from aloevera.notebook import export_notebook
    output = export_notebook(args.notebook, args.output)
    print(f"Exported: {output}")


def main():
    parser = argparse.ArgumentParser(
        prog="aloevera",
        description="aloevera — organize and export Jupyter notebooks",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")
    subparsers.required = True

    p = subparsers.add_parser(
        "export-html",
        help="Convert a notebook to HTML with a sidebar (ToC + code toggle)",
    )
    p.add_argument("notebook", help="Path to the .ipynb file")
    p.add_argument("-o", "--output", default=None, metavar="PATH",
                   help="Output .html path (default: same directory as notebook)")
    p.set_defaults(func=_cmd_export_html)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
