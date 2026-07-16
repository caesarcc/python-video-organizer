"""Planejamento, confirmação e execução das movimentações de arquivo.

Este é o único módulo autorizado a tocar o sistema de arquivos para mover arquivos. Os módulos
de detecção (duplicates.py, short_videos.py) só retornam dados; o cli.py transforma esses dados
em MovePlans e os entrega aqui. Os arquivos são sempre movidos (shutil.move), nunca copiados.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

console = Console()


@dataclass
class MovePlan:
    source: Path
    destination: Path
    reason: str = ""


def unique_destination(destination: Path) -> Path:
    """Evita sobrescrever um arquivo existente, acrescentando um sufixo numérico, ex.: 'clip (1).mp4'."""
    if not destination.exists():
        return destination
    stem, suffix, parent = destination.stem, destination.suffix, destination.parent
    counter = 1
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def show_plan(plans: list[MovePlan], title: str) -> None:
    table = Table(title=title)
    table.add_column("From", overflow="fold")
    table.add_column("To", overflow="fold")
    table.add_column("Reason")
    for plan in plans:
        table.add_row(str(plan.source), str(plan.destination), plan.reason)
    console.print(table)


def confirm(prompt: str, *, assume_yes: bool = False) -> bool:
    if assume_yes:
        return True
    return Confirm.ask(prompt, default=False)


def execute_moves(plans: list[MovePlan]) -> None:
    for plan in plans:
        plan.destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(plan.source), str(plan.destination))
        console.print(f"[green]Moved[/green] {plan.source.name} -> {plan.destination}")
