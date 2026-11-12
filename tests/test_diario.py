# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""O diario (docs/diario.html) e gerado do codigo: se uma regra mudar, ele tem que mudar junto."""
from __future__ import annotations

import html
import importlib.util
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def _gerador():
    spec = importlib.util.spec_from_file_location("gerar_diario", RAIZ / "tools" / "gerar_diario.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_o_diario_esta_em_dia():
    g = _gerador()
    assert g.DESTINO.read_text(encoding="utf-8") == g.gerar(), "rode: python tools/gerar_diario.py"


def test_o_diario_traz_os_papeis_os_nomes_e_os_numeros():
    from terror_ps1 import mapa, regras
    g = _gerador()
    texto = g.gerar()
    for papel in [mapa.BILHETE_INICIO, *mapa.TEXTOS.values()]:
        assert html.escape(papel) in texto
    for nome in mapa.NOMES_JIZO[:6] + [mapa.NOMES_JIZO[7]]:
        assert nome in texto
    assert f"{g.n(1 / regras.GASTO_PILHA)} s" in texto and f"{g.n(regras.RUIDO_PASSO['correndo'])} m" in texto


def test_numeros_a_brasileira():
    g = _gerador()
    assert (g.n(30, 0), g.n(1.6), g.n(75.0), g.n(4.5)) == ("30", "1,6", "75", "4,5")
