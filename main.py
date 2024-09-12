import typer
import requests
import mimetypes
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
import pyperclip

app = typer.Typer()
console = Console()

BASE_URL = "http://127.0.0.1:8000"


def upload_file(file_path: Path, api_key: str):
    url = f"{BASE_URL}/"
    params = {"api_key": api_key}

    if not file_path.is_file():
        console.print(
            f"[bold red]Error:[/bold red] The file '{file_path}' does not exist.", style="red")
        raise typer.Exit(code=1)

    try:
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "multipart/form-data")}
            response = requests.post(url, params=params, files=files)

        if response.status_code == 200:
            data = response.json()
            pyperclip.copy(data['file_url'])
            file_mimetype = get_mime_type(file_path)
            display_success(data, file_mimetype)
        else:
            console.print(f"[bold red]Error {
                          response.status_code}:[/bold red] {response.text}", style="red")
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Error:[/bold red] {e}", style="red")
        raise typer.Exit(code=1)


def get_mime_type(file_path: Path) -> str:
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type:
        return mime_type.split("/")[-1]
    return "unknown"


def display_success(data, file_type):
    table = Table(title="[green]File Upload Successful![/green]")

    table.add_column("Attribute", style="cyan", no_wrap=True)
    table.add_column("Details", style="magenta")

    table.add_row("File URL", data['file_url'])
    table.add_row("File Size", data['file-size'])
    table.add_row("File Type", file_type)
    table.add_row("Date Uploaded", data['date-uploaded'])

    console.print(table)


@app.command()
def upload(
    file_path: Path = typer.Argument(...,
                                     help="Path to the file you want to upload"),
    api_key: Optional[str] = typer.Option(None, help="Your API key"),
):
    if not api_key:
        console.print(
            "[bold red]Error:[/bold red] API key is required.", style="red")
        raise typer.Exit(code=1)

    console.print("[blue]Uploading file...[/blue]")
    upload_file(file_path, api_key)


if __name__ == "__main__":
    app()
