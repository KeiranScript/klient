import typer
import requests
import mimetypes
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
import webbrowser
import pyperclip

app = typer.Typer()
console = Console()

BASE_URL = "https://kuuichi.xyz"


def upload_file(file_path: Path, api_key: str):
    url = f"{BASE_URL}/"
    headers = {"Authorization": api_key}

    if not file_path.is_file():
        console.print(
            f"[bold red]Error:[/bold red] The file '{file_path}' does not exist.", style="red")
        raise typer.Exit(code=1)

    try:
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "multipart/form-data")}
            response = requests.post(
                url, headers=headers, files=files, verify=False)

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


def display_success(data, file_type):
    table = Table(title="[green]File Upload Successful![/green]")
    table.add_column("Attribute", style="cyan", no_wrap=True)
    table.add_column("Details", style="magenta")
    table.add_row("File URL", data['file_url'])
    table.add_row("Delete URL", data['delete_url'])
    table.add_row("File Size", data['file-size'])
    table.add_row("File Type", file_type)
    table.add_row("Date Uploaded", data['date-uploaded'])
    console.print(table)
    console.print("[blue]URL copied to clipboard![/blue]")
    pyperclip.copy(data['file_url'])


def get_mime_type(file_path: Path) -> str:
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type.split("/")[-1] if mime_type else "unknown"


@app.command()
def upload(file_path: Path = typer.Argument(..., help="Path to the file you want to upload"),
           api_key: Optional[str] = typer.Option(None, help="Your API key")):
    if not api_key:
        console.print(
            "[bold red]Error:[/bold red] API key is required.", style="red")
        raise typer.Exit(code=1)
    console.print("[blue]Uploading file...[/blue]")
    upload_file(file_path, api_key)


@app.command()
def list_files(api_key: Optional[str] = typer.Option(None, help="Your API key")):
    if not api_key:
        console.print(
            "[bold red]Error:[/bold red] API key is required.", style="red")
        raise typer.Exit(code=1)

    url = f"{BASE_URL}/files"
    headers = {"Authorization": api_key}

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            files_data = response.json().get("files", [])
            if not files_data:
                console.print("[yellow]No files found for the user.[/yellow]")
            else:
                display_files(files_data)
        else:
            console.print(f"[bold red]Error {
                          response.status_code}:[/bold red] {response.text}", style="red")
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Error:[/bold red] {e}", style="red")
        raise typer.Exit(code=1)


def display_files(files_data):
    table = Table(title="[green]User Files[/green]")
    table.add_column("File Name", style="cyan", no_wrap=True)
    table.add_column("File URL", style="magenta")
    table.add_column("Delete URL", style="red")
    table.add_column("File Size", style="green")
    table.add_column("File Type", style="blue")
    table.add_column("Date Uploaded", style="yellow")

    for file in files_data:
        delete_url = file.get('delete_url', 'N/A')
        table.add_row(file['file_name'], file['file_url'], delete_url,
                      file['file-size'], file['file-type'], file['date-uploaded'])
    console.print(table)


@app.command()
def info():
    url = f"{BASE_URL}/info"

    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            table = Table(title="[green]Server Information[/green]")
            table.add_column("Metric", style="cyan", no_wrap=True)
            table.add_column("Value", style="magenta")
            table.add_row("Total Storage Used", data['storage_used'])
            table.add_row("Total Uploads", str(data['uploads']))
            table.add_row("Total Users", str(data['users']))
            console.print(table)
        else:
            console.print(f"[bold red]Error {
                          response.status_code}:[/bold red] {response.text}", style="red")
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Error:[/bold red] {e}", style="red")
        raise typer.Exit(code=1)


@app.command()
def analytics():
    url = f"{BASE_URL}/analytics"

    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            display_analytics(data)
        else:
            console.print(f"[bold red]Error {
                          response.status_code}:[/bold red] {response.text}", style="red")
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Error:[/bold red] {e}", style="red")
        raise typer.Exit(code=1)


def display_analytics(data):
    table = Table(title="[green]Analytics[/green]")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")
    table.add_row("File Types", ', '.join(
        f"{k}: {v}" for k, v in data['file_types'].items()))
    table.add_row("User Uploads", ', '.join(
        f"{k}: {v}" for k, v in data['user_uploads'].items()))
    console.print(table)


@app.command()
def file_info(filename: str = typer.Argument(..., help="Name of the file to retrieve information about"),
              api_key: Optional[str] = typer.Option(None, help="Your API key"),
              copy_url: bool = typer.Option(
                  False, "-u", help="Copy the file URL to the clipboard"),
              copy_delete_url: bool = typer.Option(
                  False, "-d", help="Copy the deletion URL to the clipboard"),
              open_delete_url: bool = typer.Option(
                  False, "-D", help="Open the deletion URL in the browser"),
              copy_filename: bool = typer.Option(
                  False, "-n", help="Copy the filename to the clipboard"),
              verbose: bool = typer.Option(False, "-v", help="Display all file attributes in plain text")):

    if not api_key:
        console.print(
            "[bold red]Error:[/bold red] API key is required.", style="red")
        raise typer.Exit(code=1)

    url = f"{BASE_URL}/file_info"
    headers = {"Authorization": api_key}
    params = {"filename": filename}

    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()

            # Handle verbose output
            if verbose:
                for key, value in data.items():
                    console.print(f"{key}: {value}")
            else:
                display_file_info(data)

            # Handle clipboard operations
            if copy_url:
                pyperclip.copy(data['file_url'])
                console.print("[green]File URL copied to clipboard![/green]")

            if copy_delete_url:
                pyperclip.copy(data['delete_url'])
                console.print("[green]Delete URL copied to clipboard![/green]")

            if open_delete_url:
                webbrowser.open(data['delete_url'])
                console.print("[blue]Delete URL opened in the browser![/blue]")

            if copy_filename:
                pyperclip.copy(data['file_name'])
                console.print("[green]Filename copied to clipboard![/green]")

        else:
            console.print(f"[bold red]Error {
                          response.status_code}:[/bold red] {response.text}", style="red")
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Error:[/bold red] {e}", style="red")
        raise typer.Exit(code=1)


def display_file_info(data):
    table = Table(title="[green]File Information[/green]")
    table.add_column("Attribute", style="cyan", no_wrap=True)
    table.add_column("Details", style="magenta")
    table.add_row("File Name", data['file_name'])
    table.add_row("File URL", data['file_url'])
    table.add_row("Delete URL", data['delete_url'])
    table.add_row("File Size", data['file-size'])
    table.add_row("File Type", data['file-type'])
    table.add_row("Date Uploaded", data['date-uploaded'])
    console.print(table)
    console.print("[blue]URL copied to clipboard![/blue]")
    pyperclip.copy(data['file_url'])


if __name__ == "__main__":
    app()
