#!/usr/bin/env python3

from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from cryptography.fernet import Fernet
from getpass import getpass

import typer
import requests
import mimetypes
import pyperclip

app = typer.Typer()
console = Console()

BASE_URL = "https://kuuichi.xyz"
CONFIG_FILE = Path.home() / ".config/klu.conf"
ENCRYPTION_KEY_FILE = Path.home() / ".config/klu_key.key"


def generate_key():
    key = Fernet.generate_key()
    with open(ENCRYPTION_KEY_FILE, "wb") as key_file:
        key_file.write(key)


def load_key():
    if not ENCRYPTION_KEY_FILE.exists():
        generate_key()
    return open(ENCRYPTION_KEY_FILE, "rb").read()


def encrypt_api_key(api_key: str) -> bytes:
    fernet = Fernet(load_key())
    encrypted_key = fernet.encrypt(api_key.encode())
    return encrypted_key


def decrypt_api_key(encrypted_key: bytes) -> str:
    fernet = Fernet(load_key())
    decrypted_key = fernet.decrypt(encrypted_key).decode()
    return decrypted_key


def verify_api_key(api_key: str) -> bool:
    url = f"{BASE_URL}/verify"
    headers = {"Authorization": api_key}

    try:
        response = requests.post(url, headers=headers)
        if response.status_code == 200:
            return True
        else:
            return False
    except requests.exceptions.RequestException as e:
        console.print(
            f"[bold red]Error during API key verification:[/bold red] {e}", style="red"
        )
        return False


def handle_api_key() -> str:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "rb") as file:
            encrypted_key = file.read()
            try:
                api_key = decrypt_api_key(encrypted_key)
                if verify_api_key(api_key):
                    return api_key
                else:
                    raise ValueError("Invalid API key.")
            except Exception:
                console.print(
                    "[bold red]Error:[/bold red] Invalid API key. Please enter a new one."
                )

    while True:
        api_key = getpass("Enter your API key: ")
        if verify_api_key(api_key):
            with open(CONFIG_FILE, "wb") as file:
                file.write(encrypt_api_key(api_key))
            console.print("[green]API key saved successfully.[/green]")
            return api_key
        else:
            console.print(
                "[bold red]Error:[/bold red] Invalid API key. Please try again."
            )


def upload_file(file_path: Path, api_key: str):
    # Verify the API key before uploading
    if not verify_api_key(api_key):
        console.print("[bold red]Error:[/bold red] Invalid API key.", style="red")
        raise typer.Exit(code=1)

    url = f"{BASE_URL}/upload"
    headers = {"Authorization": api_key}

    if not file_path.is_file():
        console.print(
            f"[bold red]Error:[/bold red] The file '{
                file_path}' does not exist.",
            style="red",
        )
        raise typer.Exit(code=1)

    try:
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "multipart/form-data")}
            response = requests.post(url, headers=headers, files=files)

        if response.status_code == 200:
            data = response.json()
            pyperclip.copy(data["file_url"])
            file_mimetype = get_mime_type(file_path)
            display_success(data, file_mimetype)
        else:
            console.print(
                f"[bold red]Error {
                    response.status_code}:[/bold red] {response.text}",
                style="red",
            )
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Error:[/bold red] {e}", style="red")
        raise typer.Exit(code=1)


def display_success(data, file_type):
    table = Table(title="[green]File Upload Successful![/green]")
    table.add_column("Attribute", style="cyan", no_wrap=True)
    table.add_column("Details", style="magenta")
    table.add_row("File URL", data["file_url"])
    table.add_row("Delete URL", data["delete_url"])
    table.add_row("File Size", data["file-size"])
    table.add_row("File Type", file_type)
    table.add_row("Date Uploaded", data["date-uploaded"])
    console.print(table)
    console.print("[blue]URL copied to clipboard![/blue]")
    pyperclip.copy(data["file_url"])


def get_mime_type(file_path: Path) -> str:
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type.split("/")[-1] if mime_type else "unknown"


@app.command(help="Upload a file to the API")
def upload(
    file_path: Path = typer.Argument(..., help="Path to the file you want to upload"),
    api_key: Optional[str] = typer.Option(None, help="Your API key"),
):
    if not api_key:
        console.print("[bold red]Error:[/bold red] API key is required.", style="red")
        raise typer.Exit(code=1)
    console.print("[blue]Uploading file...[/blue]")
    upload_file(file_path, api_key)


@app.command(help="List all files you've uploaded with basic info")
def list_files(api_key: Optional[str] = typer.Option(None, help="Your API key")):
    if not api_key:
        console.print("[bold red]Error:[/bold red] API key is required.", style="red")
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
            console.print(
                f"[bold red]Error {
                    response.status_code}:[/bold red] {response.text}",
                style="red",
            )
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
        delete_url = file.get("delete_url", "N/A")
        file_url = file.get("file_url", "N/A")
        file_name = file.get("file_name", "N/A")
        file_size = file.get("file-size", "N/A")
        file_type = file.get("file-type", "N/A")
        date_uploaded = file.get("date-uploaded", "N/A")

        table.add_row(
            file_name, file_url, delete_url, file_size, file_type, date_uploaded
        )

    console.print(table)


@app.command(help="Search for files using a fuzzy match on the filename.")
def search(
    query: str,
    api_key: Optional[str] = typer.Option(None, help="Your API key"),
    limit: int = 5,
):
    if not api_key:
        console.print("[bold red]Error:[/bold red] API key is required.", style="red")
        raise typer.Exit(code=1)

    url = f"{BASE_URL}/search"
    headers = {"Authorization": api_key}
    params = {"query": query, "limit": limit}

    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            results = response.json().get("results", [])
            if results:
                display_search_results(results)
            else:
                console.print("[yellow]No matching files found.[/yellow]")
        else:
            console.print(
                f"[bold red]Error {
                    response.status_code}:[/bold red] {response.text}",
                style="red",
            )
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Error:[/bold red] {e}", style="red")
        raise typer.Exit(code=1)


def display_search_results(results):
    table = Table(title="[green]Search Results[/green]")
    table.add_column("File Name", style="cyan", no_wrap=True)
    table.add_column("File URL", style="magenta")
    table.add_column("Score (%)", style="yellow")

    for result in results:
        table.add_row(
            result["file_name"], result["file_url"], f"{int(result['score'])}%"
        )

    console.print(table)


@app.command(help="Get stats about the API")
def info():
    url = f"{BASE_URL}/info"

    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            table = Table(title="[green]Server Information[/green]")
            table.add_column("Metric", style="cyan", no_wrap=True)
            table.add_column("Value", style="magenta")
            table.add_row("Total Storage Used", data.get("storage_used", "N/A"))
            table.add_row("Total Uploads", str(data.get("uploads", "N/A")))
            table.add_row("Total Users", str(data.get("users", "N/A")))
            console.print(table)
        else:
            console.print(
                f"[bold red]Error {
                    response.status_code}:[/bold red] {response.text}",
                style="red",
            )
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Error:[/bold red] {e}", style="red")
        raise typer.Exit(code=1)


def display_analytics(data):
    table = Table(title="[green]Analytics[/green]")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")
    table.add_row(
        "File Types", ", ".join(f"{k}: {v}" for k, v in data["file_types"].items())
    )
    table.add_row(
        "User Uploads", ", ".join(f"{k}: {v}" for k, v in data["user_uploads"].items())
    )
    console.print(table)


def display_file_info(data):
    table = Table(title="[green]File Information[/green]")
    table.add_column("Attribute", style="cyan", no_wrap=True)
    table.add_column("Details", style="magenta")
    table.add_row("File Name", data["file_name"])
    table.add_row("File URL", data["file_url"])
    table.add_row("Delete URL", data["delete_url"])
    table.add_row("File Size", data["file-size"])
    table.add_row("File Type", data["file-type"])
    table.add_row("Date Uploaded", data["date-uploaded"])
    console.print(table)


if __name__ == "__main__":
    app()
