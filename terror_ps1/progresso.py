# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""O progresso salvo: a campanha (em que noite voce esta e o que ele ja sabe de voce) e as
noites ja terminadas. Fica fora da pasta do jogo (%APPDATA%/TerrorPS1), para sobreviver a
uma versao nova; a variavel TERROR_PS1_PROGRESSO aponta para outro arquivo (os testes usam)."""
from __future__ import annotations

import json
import os
from pathlib import Path


def caminho() -> Path:
    if os.environ.get("TERROR_PS1_PROGRESSO"):
        return Path(os.environ["TERROR_PS1_PROGRESSO"])
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / "TerrorPS1" / "progresso.json"


def carregar() -> dict:
    try:
        dados = json.loads(caminho().read_text(encoding="utf-8"))
        return dados if isinstance(dados, dict) else {}
    except (OSError, ValueError):
        return {}  # sem arquivo (ou estragado): comeca do zero


def _salvar(dados: dict) -> None:
    p = caminho()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def campanha() -> dict | None:
    """A campanha em andamento: {"noite_n", "aprendeu_base", "memoria"}, ou None."""
    c = carregar().get("campanha")
    return c if isinstance(c, dict) and c.get("noite_n") else None


def salvar_campanha(noite_n: int, aprendeu_base: float, memoria: dict) -> None:
    dados = carregar()
    dados["campanha"] = {"noite_n": noite_n, "aprendeu_base": aprendeu_base, "memoria": memoria}
    _salvar(dados)


def apagar_campanha() -> None:
    dados = carregar()
    dados.pop("campanha", None)
    _salvar(dados)


def concluidas() -> set[str]:
    """As noites ja terminadas ao menos uma vez ("floresta", "arrozal espelhado"...)."""
    return set(carregar().get("concluidas", []))


def marcar_concluida(bioma: str, espelho: bool) -> None:
    dados = carregar()
    feitas = set(dados.get("concluidas", []))
    feitas.add(bioma + (" espelhado" if espelho else ""))
    dados["concluidas"] = sorted(feitas)
    _salvar(dados)
