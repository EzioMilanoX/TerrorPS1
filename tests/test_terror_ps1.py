# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Demo de terror (ROADMAP M21): as regras da lanterna e do vulto, sem placa de video."""
from __future__ import annotations

import math

from terror_ps1 import regras


def _mirar_no_vulto(e: regras.Estado) -> None:
    vx, vz = e.vulto
    e.giro = math.atan2(vx - e.x, -(vz - e.z))
    e.inclina = 0.0
    e.feixe = regras.direcao(e.giro, 0.0)


def _segundos(e: regras.Estado, s: float, **kw) -> None:
    for _ in range(int(s * 60)):
        regras.atualizar(e, 1 / 60, kw.get("frente", 0.0), 0.0, 0.0, False)
        if kw.get("mirar"):
            _mirar_no_vulto(e)


def test_iluminado_o_vulto_congela():
    e = regras.Estado()
    _mirar_no_vulto(e)
    antes = e.vulto
    _segundos(e, 5, mirar=True)
    assert e.vulto == antes


def test_no_escuro_ele_chega_mais_perto():
    e = regras.Estado(acesa=False)
    d0 = math.hypot(e.x - e.vulto[0], e.z - e.vulto[1])
    _segundos(e, 3)
    assert math.hypot(e.x - e.vulto[0], e.z - e.vulto[1]) < d0 - 2


def test_olhar_para_o_outro_lado_tambem_e_escuro():
    e = regras.Estado()
    e.giro = math.pi  # de costas para a cena
    e.feixe = regras.direcao(e.giro)
    antes = e.vulto
    _segundos(e, 2)
    assert e.vulto != antes


def test_a_pilha_gasta_acesa_e_recarrega_apagada():
    e = regras.Estado()
    _segundos(e, 10, mirar=True)
    gasta = e.pilha
    assert gasta < 0.9
    regras.atualizar(e, 1 / 60, 0, 0, 0, True)  # apaga
    e.vulto = (100.0, 100.0)  # longe, para nao atrapalhar
    _segundos(e, 5)
    assert e.pilha > gasta


def test_pilha_fraca_faz_a_lanterna_falhar():
    e = regras.Estado(pilha=0.1)
    forcas = set()
    for i in range(240):
        e.tempo = i / 60
        forcas.add(round(regras.forca_da_luz(e), 2))
    assert len(forcas) > 1 and max(forcas) < 1.0


def test_quando_ele_chega_a_noite_recomeca():
    e = regras.Estado(acesa=False)
    _segundos(e, 30)
    assert e.pego > 0 or (e.x, e.z) == regras.INICIO  # pegou (e ja pode ter recomecado)
    _segundos(e, 3)
    assert e.vulto != (e.x, e.z)


def test_nao_atravessa_arvore_nem_pilar():
    e = regras.Estado(x=0.0, z=0.0, acesa=False)
    e.vulto = (100.0, 100.0)
    obstaculo = [(0.0, -2.0, 0.35)]
    for _ in range(120):  # 2 s andando reto contra o tronco
        regras.atualizar(e, 1 / 60, 1.0, 0.0, 0.0, False, obstaculos=obstaculo)
    assert math.hypot(e.x - 0.0, e.z + 2.0) >= 0.35 + regras.RAIO_JOGADOR - 1e-6


def test_o_mouse_olha_e_a_inclinacao_tem_limite():
    e = regras.Estado()
    regras.atualizar(e, 1 / 60, 0, 0, 0, False, olhar=(100.0, 0.0))
    assert e.giro > 0.2
    regras.atualizar(e, 1 / 60, 0, 0, 0, False, olhar=(0.0, -100000.0))
    assert e.inclina == regras.INCLINA_MAX


def test_o_som_do_vulto_vem_do_lado_dele():
    e = regras.Estado(x=0.0, z=0.0, giro=0.0, acesa=False)  # olhando para -z
    e.vulto = (5.0, 0.0)  # a direita
    assert regras.lado_do_vulto(e) > 0.9
    e.vulto = (-5.0, 0.0)
    assert regras.lado_do_vulto(e) < -0.9
    eventos = []
    for _ in range(90):
        regras.atualizar(e, 1 / 60, 0, 0, 0, False)
        eventos += e.eventos
    assert "vulto" in eventos  # no escuro ele anda, e da para ouvir


def test_o_coracao_acelera_com_ele_perto():
    e = regras.Estado(x=0.0, z=0.0)
    e.vulto = (20.0, 0.0)
    assert regras.batimento(e) == 0.0
    e.vulto = (6.0, 0.0)
    longe = regras.batimento(e)
    e.vulto = (2.0, 0.0)
    assert 0 < regras.batimento(e) < longe


def test_os_sons_sao_gerados_uma_vez(tmp_path):
    from terror_ps1 import sons
    caminhos = sons.gerar(tmp_path)
    assert set(caminhos) == set(sons.SONS) and all(c.stat().st_size > 1000 for c in caminhos.values())
    antes = {c: c.stat().st_mtime_ns for c in caminhos.values()}
    sons.gerar(tmp_path)
    assert {c: c.stat().st_mtime_ns for c in caminhos.values()} == antes


# ---------------------------------------------------------------- o mapa da floresta

import pytest  # noqa: E402

from terror_ps1 import mapa as mapa_mod  # noqa: E402


@pytest.fixture(scope="module")
def floresta():
    return mapa_mod.gerar_mapa()


def _no_mapa(m, **kw):
    e = regras.Estado(mapa=m)
    for k, v in kw.items():
        setattr(e, k, v)
    return e


def test_o_mapa_e_sempre_o_mesmo_e_as_trilhas_ficam_livres(floresta):
    outro = mapa_mod.gerar_mapa()
    assert floresta.arvores == outro.arvores and floresta.armadilhas == outro.armadilhas
    assert len(floresta.arvores) > 600 and len(floresta.amuletos) == 7 and len(floresta.armadilhas) >= 15
    dentro = [(x, z) for x, z, _, _ in floresta.arvores if abs(x) < mapa_mod.LIMITE and abs(z) < mapa_mod.LIMITE]
    assert all(mapa_mod.dist_trilha(p) >= 1.8 for p in dentro)  # nenhuma arvore no caminho


def test_da_para_pegar_todo_amuleto_e_toda_pilha(floresta):
    for x, z in [(a[0], a[1]) for a in floresta.amuletos] + floresta.pilhas:
        px, pz = regras.colidir(x, z, floresta.circulos_perto(x, z), floresta.caixas, (-40, 40, -40, 40))
        assert math.hypot(px - x, pz - z) < regras.PEGAR_ITEM  # a colisao deixa chegar perto o bastante


def test_pegar_amuleto_e_pilha(floresta):
    a = floresta.amuletos[0]
    x, z = regras.colidir(a[0], a[1], floresta.circulos_perto(a[0], a[1]), floresta.caixas, (-40, 40, -40, 40))
    e = _no_mapa(floresta, x=x, z=z, pilha=0.2, vulto=(a[0] + 20, a[1]))
    regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    assert e.coletados == 1 and "amuleto" in e.eventos
    p = floresta.pilhas[0]
    e.x, e.z = p[0] + 0.3, p[1]
    regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    assert e.pilha > 0.6 and "pilha" in e.eventos


def test_armadilha_prende_faz_barulho_e_o_vulto_ouve(floresta):
    tx, tz = floresta.armadilhas[0]
    e = _no_mapa(floresta, x=tx, z=tz + 0.2, vulto=(tx + 20.0, tz))
    regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    assert e.preso > 0 and "armadilha" in e.eventos and e.armadilhas[0][2] == 1.0
    assert math.hypot(e.vulto[0] - tx, e.vulto[1] - tz) <= 10.5  # correu para o barulho
    x0 = e.x
    regras.atualizar(e, 1 / 60, 1.0, 0, 0, False)
    assert e.x == x0  # preso nao anda
    for _ in range(4):  # forcando, sai antes dos 3 s
        regras.atualizar(e, 1 / 60, 0, 0, 0, False, soltar=True)
    for _ in range(120):
        regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    assert e.preso == 0 and e.mancando > 0  # solto, mas mancando
    regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    assert "armadilha" not in e.eventos  # fechada, nao morde de novo


def test_com_todos_os_amuletos_o_santuario_termina_a_noite(floresta):
    sx, sz = mapa_mod.SANTUARIO
    e = _no_mapa(floresta, x=sx, z=sz + 2.0, vulto=(sx + 15, sz + 15))
    regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    assert not e.venceu  # sem os amuletos, nada
    e.coletados, e.amuletos = 7, []
    regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    assert e.oitavo == "altar" and not e.venceu  # no altar ha oito: voce escolhe
    regras.atualizar(e, 1 / 60, 0, 0, 0, False, soltar=True)
    assert e.venceu and "venceu" in e.eventos
    regras.reiniciar(e)
    assert not e.venceu and e.coletados == 0 and len(e.amuletos) == 7


def test_longe_demais_ele_reaparece_atras(floresta):
    e = _no_mapa(floresta, vulto=(-35.0, -35.0), fase="caca")  # a noite comeca calma: aqui ja caca
    for _ in range(80):
        regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    vx, vz = e.vulto
    assert math.hypot(e.x - vx, e.z - vz) < 17 and vz > e.z  # atras (giro 0 olha para -z)


def test_caixa_nao_deixa_atravessar_parede():
    x, z = regras.colidir(0.0, 0.05, (), [(-1.0, -0.1, 1.0, 0.1)], (-9, 9, -9, 9))
    assert abs(z) >= 0.1 + regras.RAIO_JOGADOR - 1e-9


# ---------------------------------------------------------------- v0.2: o vulto que ouve, a floresta que mente

def _passos(e, n, **kw):
    eventos = []
    for _ in range(n):
        regras.atualizar(e, 1 / 60, kw.get("frente", 0.0), 0.0, kw.get("girar", 0.0), False,
                         correr=kw.get("correr", False), agachar=kw.get("agachar", False),
                         segurar_ar=kw.get("segurar_ar", False), sinalizador=kw.get("sinalizador", False))
        eventos += e.eventos
    return eventos


def test_a_noite_comeca_calma_e_o_diretor_alterna(floresta):
    e = _no_mapa(floresta)
    assert e.fase == "recuo"
    e.acesa = False
    e.fase, e.duracao_fase = "caca", regras.CACA_MAX
    for _ in range(60 * 20):
        e.vulto = (e.x + 6.0, e.z)  # segura ele a 6 m: a tensao sobe ate o pico
        regras.atualizar(e, 1 / 60, 0, 0, 0, False)
        if e.fase == "recuo" or e.pego:
            break
    assert e.fase == "recuo" and not e.pego  # no pico, ele recua


def test_no_escuro_e_quieto_ele_nao_sabe_onde_voce_esta(floresta):
    e = _no_mapa(floresta, fase="caca", acesa=False, vulto=(0.0, 20.0))
    _passos(e, 30, agachar=True, frente=1.0)
    assert e.pista is None  # agachado e no escuro, a 14 m, ele nao ouviu
    _passos(e, 120, correr=True, frente=1.0)
    assert e.pista is not None  # correndo, ouviu


def test_a_luz_acesa_te_entrega(floresta):
    e = _no_mapa(floresta, fase="caca", vulto=(0.0, 10.0))
    e.giro = math.pi / 2  # olhando para o lado: ele nao esta no feixe
    _passos(e, 2)
    assert e.pista == (e.x, e.z)


def test_correr_cansa_e_prender_o_ar_tem_limite(floresta):
    e = _no_mapa(floresta, vulto=(30.0, -30.0))
    _passos(e, 60 * 5, correr=True, frente=1.0)
    assert e.folego > 0.8
    ev = _passos(e, 60 * 8, segurar_ar=True)
    assert "arfou" in ev and e.ar < 1.0  # nao aguentou: puxou o ar alto


def test_agachado_nao_quebra_graveto_de_pe_quebra(floresta):
    gx, gz = floresta.gravetos[10]
    e = _no_mapa(floresta, x=gx, z=gz, vulto=(gx + 30, gz))
    _passos(e, 2, agachar=True)
    assert e.gravetos[10][2] == 0.0
    ev = _passos(e, 2)
    assert e.gravetos[10][2] == 1.0 and "graveto" in ev


def test_encarar_gasta_a_pilha_mais_rapido():
    e1, e2 = regras.Estado(), regras.Estado()
    _mirar_no_vulto(e1)
    e2.giro = math.pi
    e2.feixe = regras.direcao(e2.giro)
    for _ in range(300):
        regras.atualizar(e1, 1 / 60, 0, 0, 0, False)
        _mirar_no_vulto(e1)
        regras.atualizar(e2, 1 / 60, 0, 0, 0, False)
        e2.vulto = (100.0, 100.0)
    assert e1.encarando and e1.pilha < e2.pilha - 0.05


def test_quem_gira_a_lanterna_ensina_ele_a_esperar(floresta):
    e = _no_mapa(floresta)
    for _ in range(60 * 30):
        e.vulto = (e.x + 20.0, e.z + 20.0)
        regras.atualizar(e, 1 / 60, 0, 0, 1.0, False)  # girando sem parar
    assert e.aprendeu > 0.5


def test_o_diretor_faz_a_luz_falhar_na_pior_hora(floresta):
    e = _no_mapa(floresta, fase="caca")
    e.vulto = (e.x, e.z - 6.0)
    e.espera_pisca = 0.0
    _mirar_no_vulto(e)
    regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    assert e.piscando > 0 and "pisca" in e.eventos
    assert regras.forca_da_luz(e) < 1.0 or e.piscando > 0


def test_ele_imita_o_guizo(floresta):
    e = _no_mapa(floresta, fase="caca", espera_sino=0.0, acesa=False)
    e.vulto = (e.x, e.z + 12.0)  # atras de voce (giro 0 olha para -z)
    regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    assert "sino_falso" in e.eventos


def test_a_floresta_cala_com_ele_perto_e_volta_com_ele_longe(floresta):
    e = _no_mapa(floresta)
    e.x, e.z = 0.0, 30.0
    for d, quieta in ((30.0, False), (10.0, True), (16.0, True), (21.0, False)):
        e.vulto = (e.x, e.z - d)
        regras.atualizar(e, 1 / 60, 0, 0, 0, False)
        assert e.quieta == quieta, d  # cala a 13 m; so volta depois dos 19


def test_os_jizos_se_viram_quando_voce_nao_olha_e_aparece_mais_um(floresta):
    jx, jz = floresta.jizos[0]
    e = _no_mapa(floresta, vulto=(30.0, 30.0))
    e.x, e.z, e.giro = jx + 2.5, jz + 8.0, 0.0  # ao norte, olhando para eles (-z)
    regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    assert all(j[2] == 0.0 for j in e.jizos)  # antes do primeiro amuleto, a floresta e honesta
    e.coletados = 3
    regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    assert all(j[2] == 0.0 for j in e.jizos) and len(e.jizos) == 6  # olhando: nada muda
    e.giro = math.pi  # de costas
    regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    assert all(abs(j[2]) < 0.6 for j in e.jizos)  # viraram para voce (ao norte, +z)
    assert len(e.jizos) == 7


def test_no_recuo_a_floresta_mente(floresta):
    from terror_ps1 import mapa as m
    e = _no_mapa(floresta, coletados=1, vulto=(-30.0, -30.0))
    e.x, e.z, e.giro = 0.0, 30.0, math.pi  # de costas para o sul
    e.rastro = [(0.0, 10.0), (0.0, 12.5), (0.0, 15.0), (0.0, 17.5)]
    regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    assert e.pegadas and e.mentiu  # 1a mentira: pegadas saindo da trilha
    alvos = [p[2] for p in e.placas]
    e.mentiu = False
    regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    assert [p[2] for p in e.placas] != alvos  # 2a: uma placa troca de destino
    e.mentiu = False
    regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    assert e.arvore_morta == m.ARVORE_MORTA_OUTRA  # 3a: a arvore das fitas mudou de lugar
    dx, dz, y = m.AMULETO_NO_MARCO["arvore_morta"]
    assert (m.ARVORE_MORTA_OUTRA[0] + dx, m.ARVORE_MORTA_OUTRA[1] + dz, y) in e.amuletos  # e o amuleto foi junto


@pytest.mark.skip(reason="sinalizador desativado (2026-11-12)")
def test_sinalizador_congela_e_espanta(floresta):
    e = _no_mapa(floresta, fase="caca", acesa=False)
    e.vulto = (e.x + 8.0, e.z)
    ev = _passos(e, 1, sinalizador=True)
    assert "sinalizador" in ev and e.fase == "recuo" and e.sinalizadores == 0
    antes = e.vulto
    _passos(e, 60 * 3)
    assert e.vulto == antes  # na luz vermelha ele nao anda
    _passos(e, 1, sinalizador=True)
    assert e.sinalizadores == 0  # so um por noite


def test_amuletos_pesam_tilintam_e_ficam_no_altar(floresta):
    from terror_ps1.mapa import SANTUARIO
    e = _no_mapa(floresta, x=0.0, z=20.0, vulto=(30.0, 30.0), coletados=3)
    ev = _passos(e, 60, frente=1.0)
    andou_carregado = 20.0 - e.z
    assert "tilinta" in ev
    e2 = _no_mapa(floresta, x=0.0, z=20.0, vulto=(30.0, 30.0))
    _passos(e2, 60, frente=1.0)
    assert 20.0 - e2.z > andou_carregado  # sem peso, anda mais
    e.x, e.z = SANTUARIO[0], SANTUARIO[1] + 2.0
    ev = _passos(e, 1)
    assert "depositou" in ev and e.carregando == 0 and e.depositados == 3 and not e.venceu


def test_olhos_no_escuro_e_bilhetes(floresta):
    e = _no_mapa(floresta, vulto=(30.0, 30.0))
    regras.atualizar(e, 1 / 60, 0, 0, 0, True)  # apaga
    assert not e.acesa and len(e.olhos_falsos) == 4
    regras.atualizar(e, 1 / 60, 0, 0, 0, True)  # acende
    assert e.olhos_falsos == []
    x, z, _, texto = floresta.bilhetes[0]
    e.x, e.z = x + 0.5, z
    assert regras.bilhete_perto(e) == texto
    e.acesa = False
    assert "escuro" in regras.bilhete_perto(e)


# ---------------------------------------------------------------- v0.3: esconder, fotografar, Ayame, a pequena, a noite, os finais

def _usar_espaco(e):
    regras.atualizar(e, 1 / 60, 0, 0, 0, False, soltar=True)
    return list(e.eventos)


def test_esconderijo_protege_se_ele_nao_viu_e_voce_prende_o_ar(floresta):
    from terror_ps1.mapa import ESCONDERIJOS
    x, z, altura = ESCONDERIJOS["na barraca caida"]
    e = _no_mapa(floresta, x=x + 1.5, z=z, fase="caca", acesa=False, vulto=(x + 25.0, z))
    assert "escondeu" in _usar_espaco(e) and e.escondido and not e.achado
    assert abs(e.olhos()[1] - altura) < 1e-9
    e.vulto = (x + 1.0, z)  # ele passa do lado
    regras.atualizar(e, 1 / 60, 0, 0, 0, False, segurar_ar=True)
    assert not e.achado and e.pego <= 0  # prendendo o ar, ele nao acha
    regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    assert e.achado  # soltou o ar do lado dele
    e2 = _no_mapa(floresta, x=x + 1.5, z=z, fase="caca", acesa=False, vulto=(x + 8.0, z))
    e2.desde_pista = 0.5  # ele acabou de te ver
    _usar_espaco(e2)
    assert e2.escondido and e2.achado  # viu entrar: nao adianta
    assert "saiu" in _usar_espaco(e2) and not e2.escondido


def test_o_flash_cega_ele_e_gasta_filme(floresta):
    e = _no_mapa(floresta, fase="caca", acesa=False)
    e.vulto = (e.x, e.z - 6.0)  # na frente
    regras.atualizar(e, 1 / 60, 0, 0, 0, False, foto=True)
    assert "foto" in e.eventos and e.filme == regras.FILME - 1 and e.flash > 0
    antes = e.vulto
    _passos(e, 60 * 2)
    assert e.vulto == antes  # cego, nao anda
    e.filme = 0
    regras.atualizar(e, 1 / 60, 0, 0, 0, False, foto=True)
    assert "sem_filme" in e.eventos


def test_ayame_aparece_no_calmo_e_corre_para_algum_lugar(floresta):
    e = _no_mapa(floresta, coletados=1, vulto=(30.0, 30.0), espera_ayame=0.0)
    e.fase, e.duracao_fase = "recuo", 1e9
    regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    assert e.ayame is not None and "ayame" in e.eventos
    x0, z0, tx, tz, _ = e.ayame
    alvos = [(a[0], a[1]) for a in e.amuletos] + [(t[0], t[1]) for t in e.armadilhas]
    assert (tx, tz) in alvos
    regras.atualizar(e, 0.5, 0, 0, 0, False)
    if e.ayame is not None:
        assert math.hypot(e.ayame[0] - tx, e.ayame[1] - tz) < math.hypot(x0 - tx, z0 - tz)  # correu para la
    e.ayame = [e.x + 3.0, e.z, tx, tz, 5.0]
    regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    assert e.ayame is None  # chegou perto, ela some


def test_a_floresta_e_so_do_vulto(floresta):
    e = _no_mapa(floresta, coletados=7, vulto=(35.0, 35.0), fase="recuo", duracao_fase=1e9)
    _passos(e, 30)
    assert not floresta.tem_pequena and e.pequena is None


def test_a_pequena_so_anda_na_luz(floresta):
    import dataclasses
    e = _no_mapa(dataclasses.replace(floresta, tem_pequena=True), coletados=5, vulto=(35.0, 35.0), fase="recuo", duracao_fase=1e9)
    regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    assert e.pequena is not None and "pequena" in e.eventos
    e.pequena = (e.x, e.z - 6.0)  # na frente, no feixe
    e.acesa = False
    antes = e.pequena
    _passos(e, 60)
    assert e.pequena == antes  # no escuro, parada
    e.acesa = True
    e.feixe = regras.direcao(0.0, -0.13)  # apontando para ela, no chao
    e.inclina = -0.13
    for _ in range(60):
        regras.atualizar(e, 1 / 60, 0, 0, 0, False)
        e.inclina = -0.13
    assert e.pequena != antes  # na luz, anda


def test_a_chuva_abafa_o_barulho(floresta):
    e = _no_mapa(floresta, fase="caca", acesa=False, vulto=(0.0, 20.0))
    e.chuva_janela = (0.0, 1e9)
    e.chuva = 1.0
    _passos(e, 120, correr=True, frente=1.0)
    assert e.pista is None  # correndo a ~14 m, mas na chuva ele nao ouviu
    assert 0.0 <= regras.escuridao(e) < 0.01


@pytest.mark.skip(reason="diario no jogo desativado (2026-11-12)")
def test_paginas_do_diario_e_o_mapa_que_mente(floresta):
    from terror_ps1.mapa import PAGINA_MAPA
    x, z = floresta.paginas[PAGINA_MAPA]
    e = _no_mapa(floresta, x=x, z=z, vulto=(35.0, 35.0))
    regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    assert PAGINA_MAPA in e.paginas and "pagina" in e.eventos
    e.coletados, e.fase, e.mentiras = 1, "recuo", 3  # a vez do mapa
    e.x, e.z = 0.0, 30.0
    regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    assert e.mapa_trocado is not None and len(set(e.mapa_trocado)) == 2


def test_os_dois_finais_e_a_noite_seguinte(floresta):
    from terror_ps1.mapa import ALTAR_OITAVO, SANTUARIO
    sx, sz = SANTUARIO
    e = _no_mapa(floresta, x=sx, z=sz + 2.0, vulto=(sx + 15, sz + 15), coletados=7)
    e.amuletos = []
    regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    assert e.oitavo == "altar" and not e.venceu
    ev = _usar_espaco(e)
    assert e.venceu and e.fim == "amanhecer" and "venceu" in ev
    e2 = _no_mapa(floresta, x=sx, z=sz + 2.0, vulto=(sx + 15, sz + 15), coletados=7)
    e2.amuletos = []
    regras.atualizar(e2, 1 / 60, 0, 0, 0, False)
    e2.x, e2.z = ALTAR_OITAVO[0], ALTAR_OITAVO[1] + 0.5
    regras.atualizar(e2, 1 / 60, 0, 0, 0, False)
    assert e2.oitavo == "levando"
    e2.x, e2.z = sx, sz + 14.0
    regras.atualizar(e2, 1 / 60, 0, 0, 0, False)
    assert e2.venceu and e2.fim == "floresta"
    e2.memoria["esconderijos"] = ["dentro do poco"]
    regras.proxima_noite(e2)
    assert e2.noite_n == 2 and e2.mapa.bioma == "arrozal" and not e2.espelho and not e2.venceu  # os arrozais
    regras.proxima_noite(e2)
    assert e2.noite_n == 3 and e2.mapa.bioma == "aldeia" and not e2.espelho  # a aldeia
    regras.proxima_noite(e2)
    assert e2.noite_n == 4 and e2.mapa.bioma == "bambuzal" and not e2.espelho  # o bambuzal
    regras.proxima_noite(e2)
    assert e2.noite_n == 5 and e2.mapa.bioma == "cemiterio" and not e2.espelho  # o cemiterio
    regras.proxima_noite(e2)
    assert e2.noite_n == 6 and e2.mapa.bioma == "escola" and not e2.espelho  # a escola
    regras.proxima_noite(e2)
    assert e2.noite_n == 7 and e2.mapa.bioma == "torii" and not e2.espelho  # a roda
    regras.proxima_noite(e2)
    assert e2.noite_n == 8 and e2.mapa.bioma == "floresta" and e2.espelho and e2.jizo_entrada  # de novo, espelhada
    assert e2.fase == "caca" and e2.aprendeu >= 0.6 and e2.coletados == 0  # sem calma: ele ja sabe
    from terror_ps1.mapa import ESCONDERIJOS
    x, z, _ = ESCONDERIJOS["dentro do poco"]
    e2.x, e2.z, e2.vulto = x + 1.5, z, (x + 30.0, z)
    _usar_espaco(e2)
    assert e2.escondido and e2.achado  # ele lembra do poco
    regras.reiniciar(e2)
    assert e2.noite_n == 8 and e2.espelho  # morrer nao desfaz a noite seguinte


# ---------------------------------------------------------------- a segunda noite: os arrozais e o Cego

@pytest.fixture(scope="module")
def arrozais():
    from terror_ps1 import arrozal
    return arrozal.gerar_mapa()


def test_os_arrozais_tem_agua_diques_e_tudo_alcancavel(arrozais):
    from terror_ps1 import arrozal
    assert arrozais.bioma == "arrozal" and arrozais.tem_cego and not arrozais.tem_vulto
    assert arrozal.agua(0.0, 20.0) == 0  # o dique principal: seco
    assert arrozal.agua(6.0, 18.0) == 1  # a quadra de arroz: rasa
    assert arrozal.agua(-10.0, arrozal.CANAL_Z) == 2  # o canal: fundo
    assert arrozal.agua(0.0, arrozal.CANAL_Z) == 0  # a ponte
    for x, z in [(a[0], a[1]) for a in arrozais.amuletos] + arrozais.pilhas:
        px, pz = regras.colidir(x, z, arrozais.circulos_perto(x, z), arrozais.caixas, (-40, 40, -40, 40))
        assert math.hypot(px - x, pz - z) < regras.PEGAR_ITEM


def test_na_agua_se_anda_devagar_e_espirra(arrozais):
    e = regras.Estado(mapa=arrozais)
    e.cego = (35.0, -35.0)
    e.x, e.z, e.giro = 6.0, 22.0, 0.0  # dentro da quadra, andando para o norte (-z), sem sair da agua
    ev = _passos(e, 60, frente=1.0)
    na_agua = 22.0 - e.z
    assert e.na_agua == 1 and "passo_agua" in ev and e.olhos()[1] < regras.ALTURA_OLHOS - 0.2
    e2 = regras.Estado(mapa=arrozais)
    e2.cego = (35.0, -35.0)
    e2.x, e2.z, e2.giro = 0.0, 30.0, 0.0  # no dique
    _passos(e2, 60, frente=1.0)
    assert 30.0 - e2.z > na_agua * 1.4


def test_o_cego_nao_liga_para_luz_mas_corre_para_o_som(arrozais):
    e = regras.Estado(mapa=arrozais)
    e.x, e.z = 0.0, 20.0
    e.cego, e.cego_alvo = (0.0, 6.0), (0.0, 6.0)  # 14 m a frente, na luz da lanterna
    e.giro, e.feixe = 0.0, regras.direcao(0.0, 0.0)
    _passos(e, 30)
    assert e.cego != (0.0, 6.0)  # na luz, ele anda mesmo assim
    e.cego, e.cego_alvo, e.cego_correndo = (0.0, 4.0), None, False
    ev = _passos(e, 60, correr=True, frente=1.0)  # correndo: ele ouve a 16 m x 1,6
    assert "cego_ouviu" in ev and e.cego_correndo


def test_o_cego_pega_quem_esbarra_e_nao_ve_quem_se_esconde(arrozais):
    e = regras.Estado(mapa=arrozais)
    e.x, e.z = 0.0, 20.0
    e.cego, e.cego_alvo = (0.0, 21.0), (0.0, 20.0)
    regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    assert e.pego > 0 and e.quem_pegou == "cego"
    x, z, _, _ = arrozais.esconderijos["no feno do galpao"]
    e2 = regras.Estado(mapa=arrozais)
    e2.x, e2.z, e2.acesa = x + 1.2, z, False
    e2.cego = (35.0, 35.0)
    regras.atualizar(e2, 1 / 60, 0, 0, 0, False, soltar=True)
    assert e2.escondido == "no feno do galpao"
    e2.cego, e2.cego_alvo = (x + 0.8, z), (x + 0.8, z)
    regras.atualizar(e2, 1 / 60, 0, 0, 0, False, segurar_ar=True)
    assert e2.pego <= 0  # escondido e quieto: ele passa


def test_afundar_no_canal_e_o_ar_acabar(arrozais):
    from terror_ps1 import arrozal
    e = regras.Estado(mapa=arrozais)
    e.cego = (35.0, 35.0)
    e.x, e.z = -10.0, arrozal.CANAL_Z
    regras.atualizar(e, 1 / 60, 0, 0, 0, False, soltar=True)
    assert e.escondido == "submerso" and e.olhos()[1] < 0
    ev = []
    for _ in range(60 * 10):
        regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    assert e.escondido == "submerso"  # 10 s embaixo d'agua: ainda da
    for _ in range(60 * 6):
        regras.atualizar(e, 1 / 60, 0, 0, 0, False)
        ev += e.eventos
    assert not e.escondido and "arfou" in ev  # em ~15 s o ar acaba e voce sobe arfando


# ---------------------------------------------------------------- a terceira noite: a aldeia e a Imitadora

@pytest.fixture(scope="module")
def aldeia_mapa():
    from terror_ps1 import aldeia
    return aldeia.gerar_mapa()


def _na_aldeia(m, **kw):
    e = regras.Estado(mapa=m)
    for k, v in kw.items():
        setattr(e, k, v)
    return e


def test_a_aldeia_tem_tudo_alcancavel_e_bonecas(aldeia_mapa):
    m = aldeia_mapa
    assert m.bioma == "aldeia" and m.tem_imitadora and not m.tem_vulto and m.estatua == "boneca"
    assert len(m.amuletos) == 7 and len(m.espantalhos) == 10
    for x, z in [(a[0], a[1]) for a in m.amuletos] + m.pilhas:
        px, pz = regras.colidir(x, z, m.circulos_perto(x, z), m.caixas, (-40, 40, -40, 40))
        assert math.hypot(px - x, pz - z) < regras.PEGAR_ITEM


def test_a_imitadora_aparece_no_seu_caminho_e_fica_parada_enquanto_voce_olha(aldeia_mapa):
    e = _na_aldeia(aldeia_mapa, espera_imita=0.0)
    e.giro = 0.0  # olhando a rua principal, para o norte
    regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    assert e.imitadora is not None and "imitadora" in e.eventos
    x, z, _ = e.imitadora
    assert e.na_vista(x, z) and 10.0 < e.dist_imitadora() < 17.0  # na sua frente
    for _ in range(120):
        regras.atualizar(e, 1 / 60, 0, 0, 0, False)
        e.giro = 0.0
    assert e.imitadora[:2] == [x, z]  # olhando, ela nao se mexe


def test_de_as_costas_com_ela_perto_e_ela_corre(aldeia_mapa):
    e = _na_aldeia(aldeia_mapa, espera_imita=99.0)
    e.imitadora = [e.x, e.z - 8.0, 20.0]  # 8 m a frente
    e.giro = math.pi  # de costas
    d0 = e.dist_imitadora()
    regras.atualizar(e, 0.5, 0, 0, 0, False)
    assert e.dist_imitadora() < d0 - 1.0 and "imitadora_corre" in e.eventos
    for _ in range(200):
        regras.atualizar(e, 1 / 60, 0, 0, 0, False)
        if e.pego:
            break
    assert e.pego > 0 and e.quem_pegou == "imitadora"


def test_quem_se_esconde_ela_esquece(aldeia_mapa):
    from terror_ps1 import aldeia
    x, z, *_ = aldeia.ESCONDERIJOS["no armario da venda"]
    e = _na_aldeia(aldeia_mapa, espera_imita=99.0)
    e.x, e.z = x + 1.0, z - 0.5
    e.imitadora = [e.x + 3.0, e.z, 20.0]
    regras.atualizar(e, 1 / 60, 0, 0, 0, False, soltar=True)
    assert e.escondido and e.imitadora is None and "imitadora_some" in e.eventos


def test_na_aldeia_a_ayame_de_verdade_tambem_aparece_e_foge(aldeia_mapa):
    e = _na_aldeia(aldeia_mapa, coletados=1, espera_ayame=0.0, espera_imita=99.0)
    regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    assert e.ayame is not None  # a de verdade corre para algum lugar; a falsa espera


def test_correr_ate_o_folego_acabar_para_de_correr(floresta):
    e = _no_mapa(floresta, vulto=(30.0, -30.0))
    e.giro = 0.0
    ev = _passos(e, 60 * 6, correr=True, frente=1.0)
    assert "sem_folego" in ev and e.sem_folego and not e.correndo  # acabou o folego: andando
    _passos(e, 60 * 7)  # descansando
    _passos(e, 2, correr=True, frente=1.0)
    assert not e.sem_folego and e.correndo


# ---------------------------------------------------------------- a quarta noite: o bambuzal e o Farejador

@pytest.fixture(scope="module")
def bambuzal_mapa():
    from terror_ps1 import bambuzal
    return bambuzal.gerar_mapa()


def _no_bambuzal(m, **kw):
    e = regras.Estado(mapa=m)
    e.farejador = (35.0, 35.0)
    for k, v in kw.items():
        setattr(e, k, v)
    return e


def test_o_bambuzal_tem_tudo_alcancavel_e_tocos_fora_da_trilha(bambuzal_mapa):
    from terror_ps1 import bambuzal
    m = bambuzal_mapa
    assert m.bioma == "bambuzal" and m.tem_farejador and not m.tem_vulto and len(m.tocos) > 100
    assert all(bambuzal.dist_trilha(x, z) > 1.4 for x, z in m.tocos)  # a trilha e limpa
    for x, z in [(a[0], a[1]) for a in m.amuletos] + m.pilhas:
        px, pz = regras.colidir(x, z, m.circulos_perto(x, z), m.caixas, (-40, 40, -40, 40))
        assert math.hypot(px - x, pz - z) < regras.PEGAR_ITEM


def test_toco_de_pe_corta_agachado_nao(bambuzal_mapa):
    tx, tz = bambuzal_mapa.tocos[5]
    e = _no_bambuzal(bambuzal_mapa, x=tx, z=tz)
    _passos(e, 2, agachar=True)
    assert e.sangrando == 0  # agachado, o pe acha o toco
    ev = _passos(e, 2)
    assert e.sangrando > 0 and "corte" in ev and e.sangue  # de pe: cortou, ja pingou


def test_sangrando_deixa_rastro_e_ele_segue_na_ordem_lambendo(bambuzal_mapa):
    e = _no_bambuzal(bambuzal_mapa)
    e.giro = math.atan2(3.0 - e.x, -(25.0 - e.z))  # da entrada, pela trilha (sem armadilha perto)
    regras._cortar(e)
    _passos(e, 60 * 3, frente=1.0)  # andando sangrando: um rastro
    assert len(e.sangue) >= 6
    primeira = tuple(e.sangue[0][:2])
    e.farejador = (primeira[0] - 3.0, primeira[1])
    _passos(e, 60 * 3)
    assert tuple(e.sangue[0][:2]) != primeira  # lambeu a primeira e foi para a seguinte


def test_sem_sangue_ele_se_perde_e_sangue_velho_seca(bambuzal_mapa):
    e = _no_bambuzal(bambuzal_mapa)
    e.sangue = [[0.0, 0.0, -1000.0]]  # uma gota velha demais
    regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    assert e.sangue == []  # secou
    e.farejador = (e.x + 1.0, e.z)  # encostou em voce
    regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    assert e.pego > 0 and e.quem_pegou == "farejador"


def test_escondido_sem_sangrar_ele_passa_sangrando_ele_acha(bambuzal_mapa):
    from terror_ps1 import bambuzal
    x, z, *_ = bambuzal.ESCONDERIJOS["dentro do forno de carvao"]
    e = _no_bambuzal(bambuzal_mapa, x=x - 1.6, z=z)
    regras.atualizar(e, 1 / 60, 0, 0, 0, False, soltar=True)
    assert e.escondido
    e.farejador = (e.x + 0.5, e.z)
    regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    assert e.pego <= 0  # sem sangue, ele nao acha
    e.sangrando = 5.0
    regras.atualizar(e, 1 / 60, 0, 0, 0, False)
    assert e.pego > 0  # sangrando, o rastro leva ate voce


# ---------------------------------------------------------------- a quinta noite: o cemiterio e o Fantoche

@pytest.fixture(scope="module")
def cemiterio_mapa():
    from terror_ps1 import cemiterio
    return cemiterio.gerar_mapa()


def _no_cemiterio(m, acordada=True, **kw):
    e = regras.Estado(mapa=m)
    e.fantoche_acordou = acordada
    for k, v in kw.items():
        setattr(e, k, v)
    return e


def _mirar(e, ponto):
    """Vira o jogador (e o feixe, ja assentado) para um ponto (x, y, z)."""
    o = e.olhos()
    dx, dy, dz = ponto[0] - o[0], ponto[1] - o[1], ponto[2] - o[2]
    e.giro = math.atan2(dx, -dz)
    e.inclina = math.atan2(dy, math.hypot(dx, dz))
    e.feixe = regras.direcao(e.giro, e.inclina)


def test_o_cemiterio_tem_tudo_alcancavel_e_nenhum_esconderijo(cemiterio_mapa):
    from terror_ps1 import cemiterio
    m = cemiterio_mapa
    assert m.bioma == "cemiterio" and m.tem_fantoche and not m.tem_vulto and not m.esconderijos
    assert len(m.pedras) > 150 and all(cemiterio.dist_trilha(x, z) > 1.7 for x, z, _ in m.pedras)
    for x, z in [(a[0], a[1]) for a in m.amuletos] + m.pilhas:
        px, pz = regras.colidir(x, z, m.circulos_perto(x, z), m.caixas, (-40, 40, -40, 40))
        assert math.hypot(px - x, pz - z) < regras.PEGAR_ITEM


def test_ela_dorme_ate_o_primeiro_omamori(cemiterio_mapa):
    e = _no_cemiterio(cemiterio_mapa, acordada=False)
    antes = list(e.fantoche)
    _passos(e, 60)
    assert e.fantoche == antes and e.dist_fantoche() > 1e8  # deitada: nao conta como ameaca
    e.coletados = 1
    assert "fantoche_acorda" in _passos(e, 1) and e.fantoche_acordou


def test_ela_vem_sempre_virando_devagar(cemiterio_mapa):
    e = _no_cemiterio(cemiterio_mapa, x=0.0, z=20.0, acesa=False)  # sem luz: so a regra de andar
    e.fantoche = [0.0, 10.0, 0.0]  # de frente para voce (+z)
    _passos(e, 60)
    assert 10.0 + regras.FANTOCHE_VEL * 0.9 < e.fantoche[1] < 10.0 + regras.FANTOCHE_VEL * 1.1
    e.fantoche = [0.0, 10.0, math.pi]  # de costas: so gira, devagar
    _passos(e, 60)
    assert abs(e.fantoche[1] - 10.0) < 1e-6 and abs(abs(e.fantoche[2]) - (math.pi - regras.FANTOCHE_GIRO)) < 0.02


def test_luz_de_frente_nada_luz_nas_costas_ela_cai(cemiterio_mapa):
    e = _no_cemiterio(cemiterio_mapa, x=0.0, z=16.0)
    e.fantoche = [0.0, 10.0, 0.0]  # olhando para voce
    _mirar(e, (0.0, 1.3, 10.0))
    _passos(e, 30)
    assert e.fantoche_caida <= 0  # a luz bateu no rosto da morta
    e.x, e.z = 0.0, 4.0  # atras dela
    e.fantoche = [0.0, 10.0, 0.0]
    _mirar(e, regras.costas_do_fantoche(e))
    ev = _passos(e, 2)
    assert "fantoche_cai" in ev and e.fantoche_caida > 0
    parada = list(e.fantoche)
    _passos(e, 60)
    assert e.fantoche == parada  # no chao ela nao anda
    e.fantoche_caida = 0.01
    assert "fantoche_levanta" in _passos(e, 2)


def test_agarrado_segura_chuta_e_solta(cemiterio_mapa):
    e = _no_cemiterio(cemiterio_mapa, x=0.0, z=10.0, acesa=False)
    e.fantoche = [0.0, 9.0, 0.0]
    assert "agarrou" in _passos(e, 1) and e.agarrado > 0 and e.olhos()[1] < 0.5
    _passos(e, 5, correr=True)  # chutar antes de segurar nao conta
    assert e.chutes == 0
    _passos(e, 70, agachar=True)
    assert e.segurou >= regras.AGARRADO_SEGURAR
    ev = []
    for _ in range(regras.AGARRADO_CHUTES):
        ev += _passos(e, 1, correr=True) + _passos(e, 1)
    assert "soltou" in ev and e.agarrado == 0 and e.fantoche_caida > 0 and e.pego <= 0
    assert e.dist_fantoche() > 2.0  # empurrado para longe


def test_agarrado_sem_reagir_ela_leva(cemiterio_mapa):
    e = _no_cemiterio(cemiterio_mapa, x=0.0, z=10.0, acesa=False)
    e.fantoche = [0.0, 9.0, 0.0]
    _passos(e, int(60 * (regras.AGARRADO_TEMPO + 0.2)))
    assert e.pego > 0 and e.quem_pegou == "fantoche"
    e2 = _no_cemiterio(cemiterio_mapa, x=0.0, z=10.0, acesa=False, imortal=True)
    e2.fantoche = [0.0, 9.0, 0.0]
    _passos(e2, int(60 * (regras.AGARRADO_TEMPO + 0.2)))
    assert e2.pego <= 0 and e2.fantoche_caida > 0  # nao morrer: ela solta


def test_cada_monstro_tem_cinco_verdades():
    from terror_ps1 import verdades
    for quem in ("vulto", "pequena", "cego", "imitadora", "farejador", "fantoche"):
        frases = verdades.VERDADES[quem]
        assert len(frases) == verdades.ULTIMA and len(set(frases)) == verdades.ULTIMA
        assert verdades.verdade(quem, 1) == frases[0] and verdades.verdade(quem, 9) == frases[-1]
    assert verdades.verdade("ninguem", 1) == "" and verdades.verdade("vulto", 0) == ""


# ---------------------------------------------------------------- a sexta noite: a escola e a Pequena

@pytest.fixture(scope="module")
def escola_mapa():
    from terror_ps1 import escola
    return escola.gerar_mapa()


def test_a_escola_tem_tudo_alcancavel_pelas_portas(escola_mapa):
    """Anda numa grade a partir do comeco (so por onde a colisao deixa) e confere que chega perto
    de cada omamori, pilha, esconderijo e do santuario."""
    m = escola_mapa
    assert m.bioma == "escola" and m.tem_pequena and not m.tem_vulto and m.pequena_aparece == 1
    passo, lim = 0.5, m.limite - 0.5

    def livre(x, z):
        px, pz = regras.colidir(x, z, m.circulos_perto(x, z), m.caixas, (-lim, lim, -lim, lim))
        return math.hypot(px - x, pz - z) < 1e-6

    def celula(x, z):
        return round(x / passo), round(z / passo)

    ini = celula(*m.inicio)
    visto, fila = {ini}, [ini]
    while fila:
        i, j = fila.pop()
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            c = (i + di, j + dj)
            if c not in visto and livre(c[0] * passo, c[1] * passo):
                visto.add(c)
                fila.append(c)

    def chega(x, z, raio):
        return any(math.hypot(i * passo - x, j * passo - z) < raio for i, j in visto)

    for x, z, _ in m.amuletos:
        assert chega(x, z, regras.PEGAR_ITEM), (x, z)
    for x, z in m.pilhas:
        assert chega(x, z, regras.PEGAR_ITEM), (x, z)
    for nome, (x, z, *_) in m.esconderijos.items():
        assert chega(x, z, regras.ESCONDER), nome
    assert chega(*m.santuario, 2.0)


def test_a_pequena_vem_para_a_luz(escola_mapa):
    e = regras.Estado(mapa=escola_mapa)
    _passos(e, 10)
    assert e.pequena is None  # so no primeiro omamori
    e.coletados = 1
    assert "pequena" in _passos(e, 1) and e.pequena is not None
    e.x, e.z, e.giro = 0.0, 20.0, 0.0
    e.pequena = (0.0, 30.0)  # atras de voce, fora do feixe
    e.acesa = False
    _passos(e, 120)
    assert e.pequena == (0.0, 30.0)  # apagada: ela para
    e.acesa = True
    _passos(e, 120)
    andou_devagar = 30.0 - e.pequena[1]
    assert 0.5 < andou_devagar < 3.0  # acesa, mas nao nela: devagar
    assert e.dist_ameaca() == e.dist_pequena() < 10.0


# ---------------------------------------------------------------- a setima noite: o torii e a roda

@pytest.fixture(scope="module")
def torii_mapa():
    from terror_ps1 import torii
    return torii.gerar_mapa()


def _na_roda(m, quem, **kw):
    """Ja com a musica parada e `quem` atras de voce."""
    e = regras.Estado(mapa=m)
    e.x, e.z, e.giro = 0.0, 0.0, 0.0
    e.roda, e.roda_quem, e.roda_de, e.roda_meio = "atras", quem, (0.0, 0.0, 0.0), (0.0, 0.0)
    e.roda_falta = [q for q in regras.RODA_QUEM if q != quem]
    e.acesa = False
    for k, v in kw.items():
        setattr(e, k, v)
    return e


def _responder(e, quem):
    qx, qz = regras.atras_na_roda(e)
    if quem == "vulto":
        _mirar(e, (qx, 1.4, qz))
        e.acesa = True
        return _passos(e, 3)
    if quem == "imitadora":
        _mirar(e, (qx, 1.4, qz))
        return _passos(e, int(60 * (regras.RODA_ENCARAR + 0.2)))
    if quem == "pequena":
        return _passos(e, int(60 * (regras.RODA_ESCURO + 0.2)))
    if quem == "cego":
        return _passos(e, int(60 * (regras.RODA_AR + 0.2)), segurar_ar=True)
    if quem == "fantoche":
        return _passos(e, int(60 * (regras.RODA_AGACHAR + 0.2)), agachar=True)
    return _passos(e, 120, frente=1.0)  # o farejador: sair dali


def test_o_torii_e_so_a_trilha_e_a_clareira(torii_mapa):
    m = torii_mapa
    assert m.bioma == "torii" and m.tem_roda and not m.tem_vulto and not m.amuletos and not m.esconderijos
    assert len(m.bilhetes) == 1 + len(regras.RODA_QUEM)
    e = regras.Estado(mapa=m)
    assert e.roda == ""
    e.x, e.z = 0.0, 1.0
    assert "roda_canta" in _passos(e, 1) and e.roda == "canto" and not e.acesa


def test_a_roda_inteira_e_o_setimo_lugar_vazio(torii_mapa):
    e = regras.Estado(mapa=torii_mapa)
    e.x, e.z = 0.0, 1.0
    _passos(e, 1)
    vistos = []
    for _ in regras.RODA_QUEM:
        x0, z0 = e.x, e.z
        _passos(e, 30, frente=1.0)
        assert (e.x, e.z) == (x0, z0)  # olhos fechados: parado
        ev = _passos(e, int(60 * regras.RODA_CANTO))
        assert e.roda == "atras" and "roda_para" in ev
        vistos.append(e.roda_quem)
        assert len(regras.roda_lugares(e)) == len(regras.RODA_QUEM) - len(vistos)  # quem esta atras nao aparece
        assert "roda_acertou" in _responder(e, e.roda_quem), e.roda_quem
        assert e.pego <= 0 and e.acesa and e.roda_quem in [q for q, *_ in regras.roda_lugares(e)]
        _passos(e, int(60 * regras.RODA_MOSTRA) + 2)
    assert sorted(vistos) == sorted(regras.RODA_QUEM) and e.roda == "vazio"
    ev = _passos(e, int(60 * regras.RODA_CANTO) + 2)
    assert "roda_vazia" in ev and e.roda == "fim" and e.oitavo == "altar"
    assert len(regras.roda_lugares(e)) == len(regras.RODA_QUEM)  # os seis, e o lugar vazio


def test_a_roda_errar_ou_demorar_e_ser_levado(torii_mapa):
    e = _na_roda(torii_mapa, "pequena")
    e.acesa = True  # luz acesa: ela vem
    _passos(e, 2)
    assert e.pego > 0 and e.quem_pegou == "pequena"
    e = _na_roda(torii_mapa, "cego")
    _passos(e, 20, frente=1.0)  # mexeu: ele ouviu
    assert e.pego > 0 and e.quem_pegou == "cego"
    e = _na_roda(torii_mapa, "fantoche")
    _passos(e, int(60 * (regras.RODA_JANELA + 0.2)))  # nao fez nada
    assert e.pego > 0 and e.quem_pegou == "fantoche"
    e = _na_roda(torii_mapa, "vulto", imortal=True)
    assert "roda_acertou" in _passos(e, int(60 * (regras.RODA_JANELA + 0.2)))  # nao morrer: segue
    assert e.pego <= 0 and e.roda == "acertou"


# ---------------------------------------------------------------- a noite secreta: o rio

@pytest.fixture(scope="module")
def rio_mapa():
    from terror_ps1 import rio
    return rio.gerar_mapa()


def test_o_rio_nao_tem_monstro_e_ela_esta_escondida(rio_mapa):
    m = rio_mapa
    assert m.bioma == "rio" and m.tem_esconde and not m.tem_vulto and not m.amuletos
    for x, z in m.esconde_lugares:  # da para chegar perto de cada esconderijo
        px, pz = regras.colidir(x, z, m.circulos_perto(x, z), m.caixas, (-40, 40, -40, 40))
        assert math.hypot(px - x, pz - z) < regras.ACHAR and m.chao(x, z) == 0
    e = regras.Estado(mapa=m)
    _passos(e, 2)
    assert regras.ayame_escondida(e) in m.esconde_lugares and e.dist_ameaca() > 1e3  # nenhum monstro


def test_a_luz_de_longe_nao_vale_de_perto_achei_voce(rio_mapa):
    e = regras.Estado(mapa=rio_mapa)
    _passos(e, 1)
    x, z = regras.ayame_escondida(e)
    e.x, e.z = x, z + 8.0
    _mirar(e, (x, 0.7, z))
    e.acesa = True
    ev = _passos(e, 2)
    assert "ayame_corre" in ev and e.escondida_corre is not None
    _passos(e, 60 * 20)  # ela chega no lugar novo
    assert e.escondida_corre is None and regras.ayame_escondida(e) != (x, z)
    x, z = regras.ayame_escondida(e)
    e.acesa = False
    e.x, e.z = x + 1.0, z
    assert regras.pode_achar(e)
    regras.atualizar(e, 1 / 60, 0, 0, 0, False, soltar=True)
    assert e.venceu and e.fim == "achou" and "achou" in e.eventos


def test_depois_do_torii_quem_nunca_levou_o_oitavo_vai_para_o_rio(torii_mapa):
    e = regras.estado_da_noite(7)
    regras.proxima_noite(e, secreta=True)
    assert e.noite_n == 8 and e.mapa.bioma == "rio" and not e.espelho
    c = {"noite_n": 8, "aprendeu_base": 0.6, "memoria": {}}
    assert regras.noite_da_campanha({**c, "levou_oitavo": False}).mapa.bioma == "rio"
    sem = regras.noite_da_campanha({**c, "levou_oitavo": True})
    assert sem.mapa.bioma == "floresta" and sem.espelho  # levou: o rio nao abre


# ---------------------------------------------------------------- o pesadelo: espelhado, fogo, dois monstros

def test_o_pesadelo_tem_fogo_e_dois_monstros_que_se_completam():
    from terror_ps1 import mapa
    for n, bioma in enumerate(regras.FASES, start=len(regras.FASES) + 1):
        e = regras.estado_da_noite(n)
        m = e.mapa
        assert m.bioma == bioma and e.espelho and m.fogo and len(m.fogos) >= 6, bioma
        if bioma == "torii":
            continue
        par = mapa.PARES[bioma]
        assert {"pequena": m.tem_pequena, "fantoche": m.tem_fantoche, "vulto": m.tem_vulto,
                "imitadora": m.tem_imitadora}[par], bioma
        for x, z in m.fogos:  # o fogo nao fica em cima de omamori nem do comeco
            assert all(math.hypot(x - a[0], z - a[1]) > regras.PEGAR_ITEM + 0.6 for a in m.amuletos)
    assert not regras.estado_da_noite(2).mapa.fogo  # a noite normal continua igual
    arrozal = regras.estado_da_noite(len(regras.FASES) + 2)
    assert arrozal.cego is not None and arrozal.fantoche is not None


def test_no_pesadelo_a_roda_tem_menos_tempo(torii_mapa):
    import dataclasses
    e = _na_roda(dataclasses.replace(torii_mapa, fogo=True), "fantoche")
    _passos(e, int(60 * (regras.RODA_JANELA * regras.RODA_PESADELO + 0.2)))
    assert e.pego > 0

