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


def test_os_segredos_estao_la_e_a_pagina_arrancada_fora_do_indice():
    texto = _gerador().gerar()
    indice = texto[texto.index('<ol class="indice">'):texto.index("</ol>")]
    assert 'id="arrancada"' in texto and "#arrancada" not in indice
    assert 'class="noite"' in texto and 'class="lapis"' in texto and 'class="aparicao"' in texto
    assert texto.count('class="uv-mao"') >= 5


def test_o_caderno_queimado_mostra_o_pesadelo():
    from terror_ps1 import mapa
    g = _gerador()
    texto = g.gerar()
    assert 'data-modo="queimado"' in texto and 'class="fogo-tela"' in texto
    assert texto.count('class="pagina queimada"') == len(g.paginas_queimadas())
    for par in mapa.PARES_TEXTO.values():
        assert html.escape(par) in texto
    assert 'class="cinza"' in texto and "[[" not in texto
