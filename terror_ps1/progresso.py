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
    """A campanha em andamento: {"noite_n", "aprendeu_base", "memoria", "levou_oitavo"}, ou None.
    `levou_oitavo`: em alguma noite desta campanha voce levou o 8o omamori (fecha o final
    verdadeiro; ver HISTORIA.md)."""
    c = carregar().get("campanha")
    return c if isinstance(c, dict) and c.get("noite_n") else None


def salvar_campanha(noite_n: int, aprendeu_base: float, memoria: dict, levou_oitavo: bool = False) -> None:
    dados = carregar()
    dados["campanha"] = {"noite_n": noite_n, "aprendeu_base": aprendeu_base, "memoria": memoria,
                         "levou_oitavo": levou_oitavo}
    _salvar(dados)


def apagar_campanha() -> None:
    dados = carregar()
    dados.pop("campanha", None)
    _salvar(dados)


def mortes(quem: str) -> int:
    """Quantas vezes `quem` ja te pegou (em qualquer modo, desde sempre)."""
    return int(carregar().get("mortes", {}).get(quem, 0))


def morreu(quem: str) -> int:
    """Mais uma morte para `quem`; devolve a conta nova."""
    dados = carregar()
    contas = dados.get("mortes") if isinstance(dados.get("mortes"), dict) else {}
    contas[quem] = int(contas.get(quem, 0)) + 1
    dados["mortes"] = contas
    _salvar(dados)
    return contas[quem]


def trancada() -> int | None:
    """A noite sem saida em andamento (o numero dela na campanha), ou None. Enquanto houver uma,
    o jogo abre direto nela."""
    n = carregar().get("trancada")
    return n if isinstance(n, int) and n > 0 else None


def trancar(noite_n: int) -> None:
    dados = carregar()
    dados["trancada"] = noite_n
    _salvar(dados)


def destrancar() -> None:
    dados = carregar()
    if dados.pop("trancada", None) is not None:
        _salvar(dados)


def fins() -> set[str]:
    """Os finais ja vistos: "falso" (o torii, tendo levado o oitavo) e "verdadeiro" (o rio)."""
    return set(carregar().get("fins", []))


def marcar_fim(nome: str) -> None:
    dados = carregar()
    dados["fins"] = sorted(set(dados.get("fins", [])) | {nome})
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
