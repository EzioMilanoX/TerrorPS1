# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""A setima noite: o torii.

A clareira onde tudo comecou: o torii em que voce contou ate dez, de olhos fechados. Nao ha
omamori para achar. Uma trilha so, com bilhetes, ate o meio da clareira; ali a roda fecha
(`regras._roda`): os seis em volta, a musica, e quando ela para alguem esta atras de voce.
Em volta da clareira, sete pedras. Uma falta: o setimo lugar.

Mesmo contrato da floresta (`mapa.Mapa`): `gerar_mapa()` e `geometria()`.
"""
from __future__ import annotations

import math
import random

from terror_ps1.malhas import Tri, bloco, chao, lanterna, torii
from terror_ps1.mapa import MADEIRA, PEDRA, Mapa, P, _pinheiro, dist_segmento

TAMANHO = 40.0
LIMITE = 37.5
INICIO: P = (0.0, 30.0)
CENTRO: P = (0.0, 0.0)  # o meio da clareira: ali a roda fecha
SANTUARIO: P = (0.0, -6.5)  # o torii
ALTAR_OITAVO: P = (0.0, -8.0)
CLAREIRA = 9.0
TRILHA: list[P] = [INICIO, (1.5, 22.0), (-1.0, 15.0), (0.5, 9.0), CENTRO]
HISTORIA = "Setima noite. O torii. Onde voce contou ate dez."
# o que fazer com cada um, na roda (os bilhetes da trilha; a ordem e a de `regras.RODA_QUEM`)
TEXTOS = (
    "Se quebrar um galho atras de voce, e ele. Acenda a luz nele.",
    "Se forem passos pesados, e o Cego. Nao se mexa. Prenda o ar.",
    "Se for choro, e a falsa. Vire e olhe para ela.",
    "Se farejar, e o Farejador. Saia de onde voce esta.",
    "Se gemer, e ela, a de luto. Segure abaixado.",
    "Se as juntas estalarem, e a pequena. Fique no escuro.",
)
BILHETE_INICIO = "Quando a musica parar, alguem vai estar atras de voce."


def dist_trilha(x: float, z: float) -> float:
    return min(dist_segmento((x, z), TRILHA[i], TRILHA[i + 1]) for i in range(len(TRILHA) - 1))


def _aberto(x: float, z: float, folga: float = 0.0) -> bool:
    return math.hypot(x - CENTRO[0], z - CENTRO[1]) < CLAREIRA + folga or dist_trilha(x, z) < 2.2 + folga


def pedras() -> list[P]:
    """As sete pedras em volta da clareira; a do sul (a que falta) nao entra."""
    return [(CENTRO[0] + math.sin(a) * 7.0, CENTRO[1] + math.cos(a) * 7.0)
            for a in (2 * math.pi * k / 7 for k in range(7))][1:]


def gerar_mapa(semente: int = 41) -> Mapa:
    rng = random.Random(semente)
    m = Mapa(bioma="torii", nome="o torii", historia=HISTORIA, inicio=INICIO, santuario=SANTUARIO,
             limite=LIMITE, marcos={"clareira": CENTRO}, nome_marco={"clareira": "a clareira"},
             trilhas=[list(TRILHA)], esconderijos={}, altar_oitavo=ALTAR_OITAVO, tem_vulto=False,
             tem_roda=True, roda_centro=CENTRO, nevoa=(14 / 255, 15 / 255, 22 / 255), neblina_longe=20.0)
    for _ in range(3200):  # a mata fechada: so a trilha e a clareira ficam abertas
        x, z = rng.uniform(-TAMANHO - 4, TAMANHO + 4), rng.uniform(-TAMANHO - 4, TAMANHO + 4)
        if _aberto(x, z, 0.6):
            continue
        if any(math.hypot(x - a, z - b) < 1.3 for a, b, _, _ in m.arvores[-60:]):
            continue
        m.arvores.append((x, z, rng.uniform(9.0, 15.0), False))
        if abs(x) < LIMITE + 1 and abs(z) < LIMITE + 1:
            m.circulos.append((x, z, 0.4))
    for px, pz in pedras():
        m.circulos.append((px, pz, 0.35))
    sx, sz = SANTUARIO
    m.circulos += [(sx - 1.3, sz, 0.3), (sx + 1.3, sz, 0.3)]
    m.caixas.append((sx - 0.8, sz - 2.2, sx + 0.8, sz - 1.2))  # o altar
    passo = 1.0 / (len(TEXTOS) + 1)
    m.bilhetes = [(INICIO[0] + 1.5, INICIO[1] - 0.6, 0.0, BILHETE_INICIO)]
    for k, texto in enumerate(TEXTOS):  # ao longo da trilha, um de cada lado
        t = (k + 1) * passo
        i = min(int(t * (len(TRILHA) - 1)), len(TRILHA) - 2)
        f = t * (len(TRILHA) - 1) - i
        x = TRILHA[i][0] + (TRILHA[i + 1][0] - TRILHA[i][0]) * f
        z = TRILHA[i][1] + (TRILHA[i + 1][1] - TRILHA[i][1]) * f
        m.bilhetes.append((x + (1.3 if k % 2 else -1.3), z, 0.0, texto))
    m.luzes = [((sx - 1.6, 1.0, sz + 0.3), (1.4, 0.35, 0.15), 3.5),  # a lanterna de pedra do torii
               ((sx + 1.6, 1.0, sz + 0.3), (1.4, 0.35, 0.15), 3.5)]
    m.montar_grade()
    return m


def geometria(m: Mapa) -> list[Tri]:
    rng = random.Random(9)

    def cor(x, z):
        tom = rng.uniform(-5, 5)
        if math.hypot(x - CENTRO[0], z - CENTRO[1]) < CLAREIRA:
            return (int(46 + tom), int(52 + tom), int(38 + tom))  # o capim da clareira
        if dist_trilha(x, z) < 1.0:
            return (int(66 + tom), int(58 + tom), int(46 + tom))
        return (int(30 + tom), int(38 + tom), int(30 + tom))

    tris = chao(-TAMANHO - 4, TAMANHO + 4, -TAMANHO - 4, TAMANHO + 4, 1.0, cor)
    for x, z, alto, _ in m.arvores:
        tris += _pinheiro(x, z, alto, (22, 34, 28))
    for px, pz in pedras():  # as sete pedras (seis): baixas, com um babador vermelho desbotado
        tris += bloco((px, 0, pz), 0.75, 0.5, 0.36, 0.42, PEDRA)
        tris += bloco((px, 0.45, pz), 0.62, 0.46, 0.46, 0.44, (110, 40, 36))
    cx, cz = CENTRO
    tris += bloco((cx, 0, cz + 7.0), 0.04, 0.6, 0.6, 0.5, (40, 34, 28))  # onde a setima deveria estar: terra
    sx, sz = SANTUARIO
    tris += torii(sx, sz, (120, 34, 28), (70, 22, 18))
    tris += lanterna(sx - 1.6, sz + 0.3, (110, 108, 104), (255, 90, 40))
    tris += lanterna(sx + 1.6, sz + 0.3, (110, 108, 104), (255, 90, 40))
    tris += bloco((sx, 0, sz - 1.7), 0.8, 1.6, 1.6, 1.0, MADEIRA)  # o altar
    tris += bloco((sx, 0.8, sz - 1.7), 0.9, 1.8, 1.8, 1.2, (60, 40, 30))
    tris += bloco((sx + 0.35, 0, sz + 0.25), 1.15, 0.36, 0.36, 0.06, (150, 140, 120))  # a marca de quem contou
    tris += bloco((INICIO[0] + 1.5, 0, INICIO[1] - 1.0), 1.3, 0.1, 0.1, 0.1, MADEIRA)
    tris += bloco((INICIO[0] + 1.5, 1.0, INICIO[1] - 1.0), 1.35, 0.8, 0.8, 0.05, MADEIRA)
    for x, z, _, _ in m.bilhetes:
        tris += bloco((x, 0.02, z), 0.032, 0.22, 0.22, 0.3, (196, 188, 168))
    return tris
