import json
import re
import sys
import time
from typing import Any, Callable

import pandas as pd
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()


class CLInterface:
    """Interactive Command Line Interface with rich formatting."""

    def __init__(self):
        self.console = Console()

    def print_banner(self):
        banner = """
============================================================
                     TRADE ENGINE CLI
============================================================
"""
        self.console.print(banner, style="bold cyan")
        self.console.print("[bold yellow]Tip:[/bold yellow] Type `/` in menus to open command palette.")

    def typing_effect(self, text: str, delay: float = 0.01, style: str = "white"):
        for char in text:
            self.console.print(char, end="", style=style)
            time.sleep(delay)
        self.console.print()

    def show_loading(self, message: str = "Processing request...", func: Callable | None = None, *args, **kwargs):
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True,
        ) as progress:
            progress.add_task(message, total=None)
            if not func:
                time.sleep(1)
                return None
            try:
                return func(*args, **kwargs)
            except Exception as error:
                self.console.print(f"[bold red]Error:[/bold red] {str(error)}")
                return None

    @staticmethod
    def _slugify(text: str) -> str:
        text = text.strip().lower()
        text = re.sub(r"[^a-z0-9]+", "-", text)
        return text.strip("-")

    def _show_menu_palette(self, options: list[str], title: str):
        table = Table(title=f"{title} Commands", box=box.SIMPLE_HEAD, header_style="bold magenta")
        table.add_column("Slash Command", style="cyan")
        table.add_column("Action", style="white")
        for idx, option in enumerate(options, 1):
            table.add_row(f"/{idx}", option)
            table.add_row(f"/{self._slugify(option)}", option)
        table.add_row("/back", "Back (if available)")
        table.add_row("/exit", "Exit (if available)")
        self.console.print(table)

    def _show_menu_table(self, options: list[str], title: str):
        table = Table(title=title, box=box.ROUNDED, header_style="bold cyan")
        table.add_column("#", style="green", justify="right")
        table.add_column("Command", style="magenta")
        table.add_column("Action", style="white")
        for idx, option in enumerate(options, 1):
            table.add_row(str(idx), f"/{self._slugify(option)}", option)
        self.console.print(table)
        self.console.print("[dim]Type `/` to list commands, or enter number/slash command.[/dim]")

    def _resolve_slash_command(self, command: str, options: list[str], slug_map: dict[str, str]) -> str | None:
        if command.isdigit():
            index = int(command)
            if 1 <= index <= len(options):
                return options[index - 1]
            return None

        if command in slug_map:
            return slug_map[command]

        if command in {"back", "b"}:
            for option in options:
                if "back" in option.lower():
                    return option
            return None
        if command in {"exit", "quit", "q"}:
            for option in options:
                if option.lower() == "exit":
                    return option
            return None

        prefix_matches = [option for slug, option in slug_map.items() if slug.startswith(command)]
        if len(prefix_matches) == 1:
            return prefix_matches[0]
        if len(prefix_matches) > 1:
            self.console.print(
                "[yellow]Multiple matches:[/yellow] " + ", ".join(sorted(set(prefix_matches)))
            )
            return None
        return None

    def show_menu(self, options: list, title: str = "Menu", clear_screen: bool = True) -> str:
        if clear_screen:
            self.console.clear()
        normalized_options = [str(option) for option in options]
        self._show_menu_table(normalized_options, title)

        slug_map = {self._slugify(option): option for option in normalized_options}

        while True:
            try:
                raw = (self.console.input("[bold yellow]Choice: [/bold yellow]") or "").strip()
                if not raw:
                    continue

                if raw in {"/", "/?", "/help"}:
                    self._show_menu_palette(normalized_options, title)
                    continue

                if raw.startswith("/"):
                    command = raw[1:].strip().lower()
                    resolved = self._resolve_slash_command(command, normalized_options, slug_map)
                    if resolved is not None:
                        return resolved
                    self.console.print("[red]Unknown slash command. Type `/` to list commands.[/red]")
                    continue

                choice_num = int(raw)
                if 1 <= choice_num <= len(normalized_options):
                    return normalized_options[choice_num - 1]
                self.console.print("[red]Invalid choice. Please try again.[/red]")
            except ValueError:
                self.console.print("[red]Please enter a valid number or slash command.[/red]")
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Exiting...[/yellow]")
                sys.exit(0)

    def input_prompt(
        self,
        prompt: str,
        style: str = "bold yellow",
        slash_commands: dict[str, str] | None = None,
    ) -> str:
        while True:
            value = self.console.input(f"[{style}]{prompt}[/{style}]")
            if value.strip() == "/" and slash_commands:
                table = Table(title="Available Commands", box=box.SIMPLE_HEAD, header_style="bold magenta")
                table.add_column("Command", style="cyan")
                table.add_column("Action", style="white")
                for command, description in slash_commands.items():
                    table.add_row(command, description)
                self.console.print(table)
                continue
            return value

    def create_table(
        self,
        data: Any,
        title: str = "Response",
        key_columns: list | None = None,
        max_width: int | None = None,
    ) -> Table:
        table = Table(title=title, box=box.ROUNDED, show_header=True, header_style="bold magenta")
        exclude_columns = ["depth"]

        if isinstance(data, dict):
            list_keys = [key for key, value in data.items() if isinstance(value, list) and len(value) > 0]
            if list_keys:
                df = pd.DataFrame(data[list_keys[0]])
            else:
                df = pd.DataFrame([data])
        elif isinstance(data, list):
            if not data:
                table.add_column("Status", style="yellow")
                table.add_row("No data found")
                return table
            df = pd.DataFrame(data)
        else:
            table.add_column("Data", style="cyan")
            table.add_row(json.dumps(data, indent=2, default=str))
            return table

        df = df.drop(columns=[col for col in exclude_columns if col in df.columns], errors="ignore")
        if key_columns:
            available = [col for col in key_columns if col in df.columns]
            if available:
                df = df[available]

        for col in df.columns:
            col_width = min(max_width // max(len(df.columns), 1), 30) if max_width else None
            table.add_column(col, style="cyan", no_wrap=False, max_width=col_width, overflow="fold")
        for _, row in df.iterrows():
            table.add_row(*[str(val) for val in row.values])
        return table

    def display_response(self, data: Any, title: str = "Response", key_columns: list | None = None):
        table = self.create_table(data, title, key_columns)
        panel = Panel(table, title=f"[bold green]{title}[/bold green]", border_style="green", padding=(1, 2))
        self.console.print(panel)

    def display_side_by_side(
        self,
        left_data: Any,
        right_data: Any,
        left_title: str = "Left",
        right_title: str = "Right",
        left_key_columns: list | None = None,
        right_key_columns: list | None = None,
    ):
        terminal_width = self.console.width or 120
        available_width = terminal_width - 10
        left_table = self.create_table(left_data, left_title, left_key_columns, max_width=available_width)
        right_table = self.create_table(right_data, right_title, right_key_columns, max_width=available_width)
        self.console.print(Panel(left_table, title=f"[bold blue]{left_title}[/bold blue]", border_style="blue"))
        self.console.print("")
        self.console.print(Panel(right_table, title=f"[bold yellow]{right_title}[/bold yellow]", border_style="yellow"))

    def print_success(self, message: str):
        self.console.print(f"[bold green]OK: {message}[/bold green]")

    def print_error(self, message: str):
        self.console.print(f"[bold red]ERROR: {message}[/bold red]")

    def print_info(self, message: str):
        self.console.print(f"[bold blue]INFO: {message}[/bold blue]")

    def clear_screen(self):
        self.console.clear()
