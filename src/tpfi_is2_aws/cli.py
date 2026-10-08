"""Console script for tpfi_is2_aws."""

import typer
from rich.console import Console

from tpfi_is2_aws import utils

app = typer.Typer()
console = Console()


@app.command()
def main() -> None:
    """Console script for tpfi_is2_aws."""
    console.print("Replace this message by putting your code into tpfi_is2_aws.cli.main")
    console.print("See Typer documentation at https://typer.tiangolo.com/")
    utils.do_something_useful()


if __name__ == "__main__":
    app()
