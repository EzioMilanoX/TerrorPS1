# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""O menu (sem janela): o codigo secreto, as linhas do menu, o progresso salvo e as trapacas."""
from __future__ import annotations

import pytest

from terror_ps1 import menu, progresso, regras


@pytest.fixture(autouse=True)
def progresso_temporario(tmp_path, monkeypatch):
    monkeypatch.setenv("TERROR_PS1_PROGRESSO", str(tmp_path / "progresso.json"))


def _digitar(codigo, teclas):
    return [codigo.apertou({t}) for t in teclas]


def test_o_codigo_e_o_dos_outros_jogos_com_setas_ou_wasd():
    c = menu.Codigo()
    setas = ["frente", "frente", "tras", "tras", "girar_esq", "girar_dir", "girar_esq", "girar_dir"]
    assert _digitar(c, setas)[-1] is True and not any(_digitar(c, setas)[:-1])
    wasd = ["frente", "frente", "tras", "tras", "esquerda", "direita", "esquerda", "direita"]
    assert _digitar(c, wasd)[-1] is True


def test_tecla_errada_zera_mas_aproveita_o_primeiro_passo():
    c = menu.Codigo()
    _digitar(c, ["frente", "frente", "tras"])
    c.apertou({"esquerda"})  # errou
    assert c.progresso == 0
    _digitar(c, ["frente", "frente", "frente"])  # o terceiro "cima" e errado, mas vale como primeiro passo
    assert c.progresso == 1  # igual ao Hertz & Beats
    assert _digitar(c, ["frente", "tras", "tras", "girar_esq", "girar_dir", "girar_esq", "girar_dir"])[-1] is True


def test_o_menu_comum_e_o_de_desenvolvedor():
    assert menu.itens(False, None) == ["nova", "sair"]
    assert menu.itens(False, {"noite_n": 2}) == ["continuar", "nova", "sair"]
    dev = menu.itens(True, None)
    assert dev[:2] == ["nova", "sair"] and "noite:3" in dev and "espelhado" in dev and "imortal" in dev


def test_a_campanha_fica_salva_e_continua_de_onde_parou():
    assert progresso.campanha() is None
    progresso.salvar_campanha(2, 0.7, {"esconderijos": ["dentro do poco"]})
    c = progresso.campanha()
    assert c["noite_n"] == 2
    e = regras.estado_da_noite(c["noite_n"], c["aprendeu_base"], c["memoria"])
    assert e.mapa.bioma == "arrozal" and e.noite_n == 2 and e.memoria["esconderijos"] == ["dentro do poco"]
    progresso.marcar_concluida("floresta", False)
    progresso.marcar_concluida("arrozal", True)
    assert progresso.concluidas() == {"floresta", "arrozal espelhado"}
    progresso.apagar_campanha()
    assert progresso.campanha() is None and progresso.concluidas()  # concluidas ficam


def test_arquivo_estragado_nao_derruba_o_jogo(tmp_path, monkeypatch):
    ruim = tmp_path / "ruim.json"
    ruim.write_text("{nao e json", encoding="utf-8")
    monkeypatch.setenv("TERROR_PS1_PROGRESSO", str(ruim))
    assert progresso.campanha() is None and progresso.concluidas() == set()


def test_trapacas_nao_morrer_pilha_e_filme():
    e = regras.estado_da_noite(1)
    e.imortal, e.pilha_infinita, e.filme_infinito = True, True, True
    e.fase, e.acesa = "caca", False
    e.vulto = (e.x, e.z - 0.5)  # em cima de voce
    for _ in range(120):
        regras.atualizar(e, 1 / 60, 0, 0, 0, False, foto=(_ == 0))
    assert e.pego <= 0 and e.pilha == 1.0 and e.filme == regras.FILME
    regras.reiniciar(e)
    assert e.imortal  # a trapaca sobrevive ao recomeco
