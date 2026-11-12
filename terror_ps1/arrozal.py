# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""A segunda noite: os arrozais alagados.

Campo aberto: quadras de arroz cheias d'agua entre diques de terra, um canal fundo que
corta tudo de leste a oeste (com uma ponte so), espantalhos que se viram para voce, e a
neblina mais grossa. Na agua se anda devagar e cada passo espirra -- e aqui quem caca e o
Cego: enorme, lento, nao liga para luz nenhuma, mas ouve tudo.

Mesmo contrato da floresta (`mapa.Mapa`): `gerar_mapa()` decide onde fica cada coisa,
`geometria()` faz os triangulos do que nunca muda.
"""
from __future__ import annotations

import math
import random

from terror_ps1.malhas import Tri, bloco, chao, cone, icosaedro, lanterna, torii
from terror_ps1.mapa import (
    MADEIRA,
    MADEIRA_ESCURA,
    PEDRA,
    Mapa,
    P,
    _arvore_seca,
    _pinheiro,
    dist_segmento,
)

TAMANHO = 40.0
LIMITE = 37.5
INICIO: P = (0.0, 34.0)
SANTUARIO: P = (0.0, -31.0)
ALTAR_OITAVO: P = (0.0, -32.8)
CANAL_Z, CANAL_MEIA = -4.0, 2.5  # o canal fundo: z entre -6,5 e -1,5
PONTE_MEIA = 1.1  # a ponte cobre x entre -1,1 e 1,1
CEGO_INICIO: P = (-20.0, -26.0)

# os diques: por onde se anda no seco
TRILHAS: list[list[P]] = [
    [INICIO, (0.0, -1.5)], [(0.0, -6.5), SANTUARIO],
    [(-34.0, 24.0), (34.0, 24.0)], [(-34.0, 12.0), (34.0, 12.0)], [(-34.0, 2.0), (34.0, 2.0)],
    [(-34.0, -0.8), (34.0, -0.8)], [(-34.0, -7.2), (34.0, -7.2)],
    [(-34.0, -12.0), (34.0, -12.0)], [(-34.0, -22.0), (34.0, -22.0)],
    [(-24.0, 24.0), (-24.0, 2.0)], [(-24.0, -12.0), (-24.0, -30.0)], [(-12.0, 12.0), (-12.0, 2.0)],
    [(12.0, 24.0), (12.0, 2.0)], [(12.0, -12.0), (12.0, -22.0)],
    [(24.0, 12.0), (24.0, 2.0)], [(24.0, -12.0), (24.0, -30.0)],
]
MARCOS: dict[str, P] = {
    "galpao": (-18.0, 18.0), "ponte": (0.0, -4.0), "espantalho": (18.0, 18.0), "roda": (28.0, -4.5),
    "tumulo": (-18.0, -17.0), "casa_bomba": (17.0, -17.0), "barco": (-30.0, 0.2),
}
NOME_MARCO = {"galpao": "o galpao", "ponte": "a ponte", "espantalho": "o espantalho grande",
              "roda": "a roda d'agua", "tumulo": "o tumulo", "casa_bomba": "a casa da bomba", "barco": "o barco virado"}
AMULETO_NO_MARCO = {"galpao": (-0.8, 0.4, 0.9), "ponte": (0.9, 0.0, 1.1), "espantalho": (0.0, 0.7, 1.6),
                    "roda": (0.0, 3.4, 0.6), "tumulo": (0.0, 1.0, 0.6), "casa_bomba": (0.0, 2.0, 0.7),
                    "barco": (2.4, 0.0, 0.4)}
# chao seco fora dos diques: (x, z, raio)
SECOS = [(-18.0, 18.0, 5.5), (-18.0, -17.0, 3.5), (17.0, -17.0, 3.2), (0.0, -31.0, 5.0), (0.0, 34.0, 4.5),
         (28.0, -0.2, 1.6)]
ESCONDERIJOS = {
    "no feno do galpao": (-20.6, 19.4, 0.55, "seco"),
    "embaixo da ponte": (1.4, -1.7, 0.35, "seco"),
}
HISTORIA = "Segunda noite. Os arrozais alagados. Algo enorme anda na agua -- e nao enxerga."
TEXTOS = {
    "galpao": "Ele nao enxerga. Ele ouve. Ouve ate a agua mexendo. Fique na terra dos diques e ande devagar.",
    "ponte": "Debaixo da ponte tem um vao seco. Cabe uma pessoa. Cabia duas.",
    "tumulo": "Aqui jaz o guarda da represa. Na noite da enchente ele furou os proprios olhos para nao ver a "
              "agua subir. Nunca mais saiu dela.",
    "casa_bomba": "No canal da para afundar e sumir (ESPACO). O ar dura uns quinze segundos.",
    "barco": "O barco virou com tres dentro. So o omamori voltou para a margem.",
    "espantalho": "Os espantalhos nao espantam nada. Eles olham.",
}
BILHETE_INICIO = "ARROZAIS -- PROIBIDO ENTRAR NA AGUA DEPOIS DO ESCURO."


def dist_dique(x: float, z: float) -> float:
    return min(dist_segmento((x, z), t[i], t[i + 1]) for t in TRILHAS for i in range(len(t) - 1))


def agua(x: float, z: float) -> int:
    """0 seco (diques, quintais, ponte), 1 raso (as quadras de arroz), 2 fundo (o canal)."""
    if abs(x) > LIMITE + 0.5 or abs(z) > LIMITE + 0.5:
        return 0
    if abs(z - CANAL_Z) < CANAL_MEIA:
        return 0 if abs(x) < PONTE_MEIA else 2
    if dist_dique(x, z) < 0.9 or any(math.hypot(x - a, z - b) < r for a, b, r in SECOS):
        return 0
    return 1


def gerar_mapa(semente: int = 11) -> Mapa:
    rng = random.Random(semente)
    m = Mapa(bioma="arrozal", nome="os arrozais", historia=HISTORIA, inicio=INICIO, santuario=SANTUARIO,
             limite=LIMITE, marcos=dict(MARCOS), nome_marco=dict(NOME_MARCO), trilhas=TRILHAS,
             esconderijos=dict(ESCONDERIJOS), altar_oitavo=ALTAR_OITAVO, amuleto_no_marco=dict(AMULETO_NO_MARCO),
             tem_vulto=False, tem_pequena=False, tem_cego=True, cego_inicio=CEGO_INICIO, agua=agua,
             nevoa=(40 / 255, 44 / 255, 52 / 255), neblina_longe=21.0)
    for nome, (mx, mz) in MARCOS.items():
        dx, dz, y = AMULETO_NO_MARCO[nome]
        m.amuletos.append((mx + dx, mz + dz, y))
    _colisao(m)
    ocupado: list[P] = []
    for _ in range(5000):  # a mata em volta: uma parede alem do limite
        x, z = rng.uniform(-TAMANHO - 4, TAMANHO + 4), rng.uniform(-TAMANHO - 4, TAMANHO + 4)
        if abs(x) < LIMITE + 1 and abs(z) < LIMITE + 1:
            continue
        if any(abs(x - a) < 1.3 and abs(z - b) < 1.3 for a, b in ocupado[-60:]):
            continue
        ocupado.append((x, z))
        m.arvores.append((x, z, rng.uniform(8.0, 13.0), rng.random() < 0.1))
    for _ in range(400):  # umas arvores secas soltas nos diques largos
        if len([a for a in m.arvores if abs(a[0]) < LIMITE]) >= 7:
            break
        x, z = rng.uniform(-32, 32), rng.uniform(-28, 28)
        if agua(x, z) == 0 and dist_dique(x, z) < 0.8 and dist_dique(x, z) > 0.3 and _longe_de_tudo(x, z, 5.0):
            m.arvores.append((x + 0.9, z, rng.uniform(6.0, 8.0), True))
            m.circulos.append((x + 0.9, z, 0.3))
    while len(m.espantalhos) < 16:  # espantalhos no meio da agua
        x, z = rng.uniform(-33, 33), rng.uniform(-28, 30)
        if agua(x, z) == 1 and dist_dique(x, z) > 2.5 and _longe_de_tudo(x, z, 4.0) and all(
                math.hypot(x - a, z - b) > 6 for a, b in m.espantalhos):
            m.espantalhos.append((x, z))
            m.circulos.append((x, z, 0.25))
    pontos = [(t, 0) for t in TRILHAS]
    while len(m.armadilhas) < 10:  # armadilhas: nos diques (o seco tem preco)
        t, _ = rng.choice(pontos)
        k = rng.random()
        x = t[0][0] + (t[1][0] - t[0][0]) * k
        z = t[0][1] + (t[1][1] - t[0][1]) * k
        longe = [INICIO, SANTUARIO, *MARCOS.values()] + m.armadilhas
        if agua(x, z) == 0 and abs(z - CANAL_Z) > 3.5 and all(math.hypot(x - p[0], z - p[1]) > 5.0 for p in longe):
            m.armadilhas.append((x, z))
    m.pilhas = [(-6.0, 12.6), (6.0, -12.6), (-24.6, -18.0), (24.6, 8.0), (30.0, 24.6)]
    m.bilhetes = [(INICIO[0] + 1.5, INICIO[1] - 0.6, 0.0, BILHETE_INICIO)]
    lugar = {"galpao": (-17.0, 19.6, 0.0), "ponte": (1.4, -0.9, 0.0), "tumulo": (-16.8, -16.0, 0.0),
             "casa_bomba": (18.6, -15.4, 0.0), "barco": (-27.0, 1.0, 0.0), "espantalho": (18.0, 12.6, 0.0)}
    m.bilhetes += [(*lugar[k], t) for k, t in TEXTOS.items()]
    m.luzes = [((-19.0, 1.8, 18.0), (1.2, 0.6, 0.25), 5.0),  # o lampiao no galpao
               ((-18.0, 0.5, -16.4), (1.0, 0.75, 0.35), 2.8),  # a vela no tumulo
               ((17.0, 2.5, -15.4), (0.55, 0.9, 0.7), 4.0),  # a lampada da casa da bomba, esverdeada
               ((-1.0, 1.0, -31.6), (1.5, 0.3, 0.15), 3.0)]  # a vela do santuario
    m.montar_grade()
    return m


def _longe_de_tudo(x: float, z: float, r: float) -> bool:
    return all(math.hypot(x - a, z - b) > r for a, b in [INICIO, SANTUARIO, *MARCOS.values()])


def _colisao(m: Mapa) -> None:
    gx, gz = MARCOS["galpao"]  # o galpao: porta para o leste
    m.caixas += [(gx - 3.1, gz - 2.6, gx + 3.1, gz - 2.4), (gx - 3.1, gz + 2.4, gx + 3.1, gz + 2.6),
                 (gx - 3.1, gz - 2.6, gx - 2.9, gz + 2.6), (gx + 2.9, gz - 2.6, gx + 3.1, gz - 0.9),
                 (gx + 2.9, gz + 0.9, gx + 3.1, gz + 2.6)]
    bx, bz = MARCOS["casa_bomba"]
    m.caixas.append((bx - 1.5, bz - 1.5, bx + 1.5, bz + 1.5))
    m.circulos += [(MARCOS["tumulo"][0], MARCOS["tumulo"][1], 0.5), (MARCOS["espantalho"][0], MARCOS["espantalho"][1], 0.3)]
    rx, rz = MARCOS["roda"]
    m.caixas.append((rx - 0.4, rz - 2.0, rx + 0.4, rz + 2.0))
    ax, az = MARCOS["barco"]
    m.caixas.append((ax - 2.0, az - 0.7, ax + 2.0, az + 0.7))
    sx, sz = SANTUARIO
    m.caixas.append((sx - 1.0, sz - 4.0, sx + 1.0, sz - 2.6))  # o santuario (hokora)
    m.circulos += [(sx - 1.3, sz + 1.5, 0.3), (sx + 1.3, sz + 1.5, 0.3)]  # o torii
    m.caixas += [(-PONTE_MEIA - 0.15, CANAL_Z - 3.0, -PONTE_MEIA, CANAL_Z + 3.0),  # o corrimao da ponte
                 (PONTE_MEIA, CANAL_Z - 3.0, PONTE_MEIA + 0.15, CANAL_Z + 3.0)]


# ------------------------------------------------------------------ geometria

def _galpao(x, z) -> list[Tri]:
    t: list[Tri] = []
    for x0, z0, x1, z1 in [(-3.1, -2.6, 3.1, -2.4), (-3.1, 2.4, 3.1, 2.6), (-3.1, -2.6, -2.9, 2.6),
                           (2.9, -2.6, 3.1, -0.9), (2.9, 0.9, 3.1, 2.6)]:
        t += bloco((x + (x0 + x1) / 2, 0, z + (z0 + z1) / 2), 2.6, x1 - x0, x1 - x0, z1 - z0, MADEIRA_ESCURA)
    t += bloco((x, 2.6, z), 4.3, 6.8, 0.3, 5.6, (52, 40, 34))  # o telhado
    for dx, dz in ((-2.0, 1.4), (-2.0, 0.4), (-1.2, 1.6), (-2.2, -1.5)):  # fardos de feno
        t += bloco((x + dx, 0, z + dz), 0.6, 0.9, 0.9, 0.6, (150, 128, 70))
    t += bloco((x - 0.8, 0, z + 0.4), 0.8, 0.7, 0.7, 0.7, MADEIRA)  # o caixote do amuleto
    t += bloco((x - 1.0, 1.6, z), 1.85, 0.1, 0.07, 0.1, (220, 160, 80), emissivo=True)  # o lampiao
    return t


def _ponte() -> list[Tri]:
    t = bloco((0, 0.05, CANAL_Z), 0.35, 2 * PONTE_MEIA + 0.2, 2 * PONTE_MEIA + 0.2, 2 * CANAL_MEIA + 1.4, MADEIRA)
    for sx in (-1, 1):
        x = sx * (PONTE_MEIA + 0.07)
        for dz in (-3.0, -1.0, 1.0, 3.0):
            t += bloco((x, -0.6, CANAL_Z + dz), 1.2, 0.12, 0.1, 0.12, MADEIRA_ESCURA)
        t += bloco((x, 1.05, CANAL_Z), 1.15, 0.08, 0.08, 6.2, MADEIRA_ESCURA)
    return t


def _espantalho_grande(x, z) -> list[Tri]:
    pano = (96, 70, 60)
    t = bloco((x, 0, z), 3.0, 0.12, 0.1, 0.12, MADEIRA)
    t += bloco((x, 2.1, z), 2.2, 2.6, 2.6, 0.1, MADEIRA)  # os bracos
    t += bloco((x, 1.2, z), 2.2, 0.8, 0.9, 0.3, pano)  # o casaco
    t += icosaedro((x, 2.55, z), 0.25, (176, 160, 120))  # a cabeca de saco
    t += cone((x, 2.72, z), 0.6, 0.35, (170, 150, 90), lados=8)  # o chapeu de palha
    return t


def malha_espantalho() -> list[Tri]:
    """Um espantalho comum (centrado na origem, olhando para +z): o rosto de saco tem dois
    furos e uma boca costurada -- e ele se vira para voce."""
    t = bloco((0, 0, 0), 2.1, 0.08, 0.07, 0.08, MADEIRA)
    t += bloco((0, 1.5, 0), 1.58, 1.7, 1.7, 0.07, MADEIRA)
    t += bloco((0, 0.8, 0), 1.6, 0.55, 0.6, 0.22, (74, 66, 58))
    t += icosaedro((0, 1.85, 0), 0.19, (170, 156, 120))
    for dx in (-0.07, 0.07):
        t += bloco((dx, 1.87, 0.17), 1.92, 0.04, 0.04, 0.03, (14, 10, 10))
    t += bloco((0, 1.76, 0.17), 1.78, 0.12, 0.12, 0.03, (40, 20, 18))
    return t + cone((0, 2.0, 0), 0.42, 0.25, (150, 132, 80), lados=7)


def _roda(x, z) -> list[Tri]:
    t: list[Tri] = []
    cy = 1.4
    for k in range(10):  # as pas, em volta do eixo (que corre em z)
        a = k * 2 * math.pi / 10
        base = (x + 1.5 * math.cos(a), cy + 1.5 * math.sin(a), z)
        t += bloco(base, base[1] + 0.6, 0.12, 0.12, 1.6, MADEIRA_ESCURA, a - math.pi / 2, base)
    t += bloco((x, cy - 0.15, z), cy + 0.15, 0.3, 0.3, 2.2, MADEIRA)  # o eixo
    t += bloco((x, -0.5, z - 1.2), cy + 0.3, 0.25, 0.2, 0.25, MADEIRA)
    t += bloco((x, -0.5, z + 1.2), cy + 0.3, 0.25, 0.2, 0.25, MADEIRA)
    return t


def _tumulo(x, z) -> list[Tri]:
    monte = icosaedro((x, 0.0, z), 1.6, (58, 50, 40), sub=1)
    t = [tuple((p[0], max(0.0, p[1]) * 0.35, p[2]) for p in tri[:3]) + tri[3:] for tri in monte]
    t += bloco((x, 0, z + 0.2), 1.3, 0.5, 0.42, 0.18, PEDRA)  # a lapide
    for k in range(5):
        a = k * 1.25
        t += bloco((x + 1.8 * math.cos(a), 0, z + 1.8 * math.sin(a)), 0.25, 0.3, 0.2, 0.3, PEDRA)
    t += bloco((x, 0.3, z + 0.6), 0.45, 0.05, 0.05, 0.05, (240, 220, 160), emissivo=True)  # a vela
    return t


def _casa_bomba(x, z) -> list[Tri]:
    concreto = (104, 104, 98)
    t = bloco((x, 0, z), 2.4, 3.0, 3.0, 3.0, concreto)
    t += bloco((x, 2.4, z), 2.55, 3.4, 3.4, 3.4, (70, 70, 66))
    t += bloco((x, 0, z + 1.52), 1.9, 0.9, 0.9, 0.04, (24, 24, 26))  # a porta escura
    t += bloco((x, 2.2, z + 1.6), 2.3, 0.15, 0.15, 0.15, (180, 255, 200), emissivo=True)  # a lampada
    t += bloco((x + 1.0, 0, z + 1.9), 0.25, 0.8, 0.8, 0.6, concreto)  # o degrau
    return t


def _barco(x, z) -> list[Tri]:
    casco = (60, 46, 38)
    t = bloco((x, 0, z), 0.75, 1.5, 0.7, 4.0, casco, 0.0)
    return [tuple((p[2] - z + x, p[1], p[0] - x + z) for p in tri[:3]) + tri[3:] for tri in t]  # de lado na margem


def _santuario() -> list[Tri]:
    sx, sz = SANTUARIO
    t = torii(sx, sz + 1.5, (100, 30, 26), (64, 20, 18), inclina=math.radians(-2))
    t += lanterna(sx - 1.6, sz + 0.2, (110, 108, 104), (255, 70, 40))
    t += bloco((sx, 0, sz - 3.3), 1.4, 1.8, 1.8, 1.3, MADEIRA_ESCURA)  # o hokora
    t += bloco((sx, 1.4, sz - 3.3), 2.0, 2.4, 0.2, 1.9, (40, 30, 28))
    t += bloco((sx, 0, sz - 1.8), 0.7, 1.0, 1.0, 0.6, PEDRA)  # o altar
    return t


def geometria(m: Mapa) -> list[Tri]:
    rng = random.Random(3)

    def cor(x, z):
        tom = rng.uniform(-5, 5)
        tipo = agua(x, z)
        if tipo == 2:
            return (int(18 + tom), int(22 + tom), int(28 + tom))  # o canal, preto
        if tipo == 1:
            return (int(44 + tom), int(52 + tom), int(62 + tom))  # agua parada, refletindo a lua
        if dist_dique(x, z) < 0.9 and rng.random() < 0.3:
            return (int(48 + tom), int(56 + tom), int(36 + tom))  # capim no dique
        return (int(64 + tom), int(57 + tom), int(45 + tom))

    def altura(x, z):
        tipo = agua(x, z)
        return -0.25 if tipo == 2 else 0.0 if tipo == 1 else 0.18

    tris = chao(-TAMANHO - 4, TAMANHO + 4, -TAMANHO - 4, TAMANHO + 4, 0.7, cor, altura)
    for x, z, alto, seca in m.arvores:
        tris += _arvore_seca(x, z, alto * 0.75) if seca else _pinheiro(x, z, alto, (30, 40, 36))
    rb = random.Random(5)
    for _ in range(420):  # o arroz que ninguem colheu
        x, z = rb.uniform(-LIMITE, LIMITE), rb.uniform(-LIMITE, LIMITE)
        if agua(x, z) == 1:
            tris += cone((x, 0, z), 0.13, rb.uniform(0.35, 0.6), (96, 104, 62), lados=4)
    for k in range(6):  # postes de luz apagados ao longo do dique principal
        z = 30.0 - k * 11.0
        if abs(z - CANAL_Z) > 4:
            tris += bloco((1.4, 0, z), 6.0, 0.18, 0.13, 0.18, (50, 44, 40))
            tris += bloco((1.4, 5.5, z), 5.62, 1.4, 1.4, 0.08, (50, 44, 40))
    construtores = {"galpao": _galpao, "espantalho": _espantalho_grande, "roda": _roda, "tumulo": _tumulo,
                    "casa_bomba": _casa_bomba, "barco": _barco}
    for nome, (x, z) in MARCOS.items():
        if nome in construtores:
            tris += construtores[nome](x, z)
    tris += _ponte() + _santuario()
    tris += bloco((INICIO[0] + 1.5, 0, INICIO[1] - 1.0), 1.3, 0.1, 0.1, 0.1, MADEIRA)
    tris += bloco((INICIO[0] + 1.5, 1.0, INICIO[1] - 1.0), 1.35, 0.8, 0.8, 0.05, MADEIRA)
    for x, z, y, _ in m.bilhetes:
        y0 = y if y > 0.1 else 0.2
        tris += bloco((x, y0, z), y0 + 0.012, 0.22, 0.22, 0.3, (196, 188, 168))
    return tris


def malha_cego() -> list[Tri]:
    """O Cego: enorme (mais de 3 m), curvado para a frente, a cabeca enfaixada sem rosto e os
    bracos arrastando na agua. Olha para +z."""
    pele, faixa, escuro = (126, 118, 108), (180, 172, 150), (20, 14, 12)
    t = bloco((0, 1.4, -0.2), 2.6, 0.9, 1.2, 0.7, pele, 0.0)  # o tronco
    t = [tuple((p[0], p[1], p[2] + (p[1] - 1.4) * 0.45) for p in tri[:3]) + tri[3:] for tri in t]  # curvado
    for dx in (-0.28, 0.28):
        t += bloco((dx, 0, -0.1), 1.5, 0.22, 0.26, 0.24, pele)  # pernas
        t += bloco((dx * 2.2, 0.15, 0.6), 2.5, 0.12, 0.2, 0.14, pele, 0.25 if dx > 0 else -0.25, (dx * 2.2, 2.5, 0.6))
    cabeca = icosaedro((0, 2.75, 0.75), 0.3, faixa, sub=1)
    t += [tuple((p[0], p[1], p[2]) for p in tri[:3]) + tri[3:] for tri in cabeca]
    t += bloco((0, 2.62, 1.0), 2.7, 0.2, 0.24, 0.06, escuro)  # a boca, a unica coisa no rosto
    for k in range(3):  # as voltas da faixa
        t += bloco((0, 2.7 + k * 0.12, 0.75), 2.74 + k * 0.12, 0.62, 0.62, 0.62, (150, 140, 120))
    return t
