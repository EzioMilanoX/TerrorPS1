# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""A sexta noite: a escola.

A escola primaria da aldeia, fechada. O patio de terra, o ginasio, a piscina vazia, a coelheira e
o predio de madeira: o corredor, a sapateira, a enfermaria, as salas, a sala de musica. Atras do
predio, o santuario. Quem anda aqui e a Pequena, a menina que sumiu antes da Ayame e que
ninguem foi procurar. Ela tem medo do escuro: vem para a luz (`regras._pequena`).

Mesmo contrato da floresta (`mapa.Mapa`): `gerar_mapa()` e `geometria()`.
"""
from __future__ import annotations

import math
import random

from terror_ps1.malhas import Tri, bloco, chao, lanterna, torii
from terror_ps1.mapa import MADEIRA, MADEIRA_ESCURA, PEDRA, Mapa, P, _pinheiro, dist_segmento

TAMANHO = 40.0
LIMITE = 37.5
INICIO: P = (0.0, 34.0)
SANTUARIO: P = (0.0, -31.0)
ALTAR_OITAVO: P = (0.0, -32.8)

# o predio: x de -26 a 26, z de -12 (fundos) a -2 (frente); o corredor de -5 a -2
PREDIO = (-26.0, -12.0, 26.0, -2.0)
CORREDOR_Z = -5.0
PAREDE = 0.3
ALTO = 3.0  # o teto do terreo
# as paredes (x0, z0, x1, z1); os vaos sao as portas
PAREDES: list[tuple[float, float, float, float]] = [
    # a frente: porta do lado oeste, a entrada principal, porta do lado leste
    (-26.0, -2.0, -21.0, -2.0), (-19.0, -2.0, -1.6, -2.0), (1.6, -2.0, 19.0, -2.0), (21.0, -2.0, 26.0, -2.0),
    # os fundos: a porta do saguao, para o santuario
    (-26.0, -12.0, -1.6, -12.0), (1.6, -12.0, 26.0, -12.0),
    (-26.0, -12.0, -26.0, -2.0), (26.0, -12.0, 26.0, -2.0),
    # o corredor: uma porta para cada sala (o saguao, no meio, e aberto)
    (-26.0, CORREDOR_Z, -20.2, CORREDOR_Z), (-18.6, CORREDOR_Z, -9.2, CORREDOR_Z), (-7.6, CORREDOR_Z, -4.0, CORREDOR_Z),
    (4.0, CORREDOR_Z, 7.6, CORREDOR_Z), (9.2, CORREDOR_Z, 18.6, CORREDOR_Z), (20.2, CORREDOR_Z, 26.0, CORREDOR_Z),
    # entre as salas
    (-13.0, -12.0, -13.0, CORREDOR_Z), (-4.0, -12.0, -4.0, CORREDOR_Z),
    (4.0, -12.0, 4.0, CORREDOR_Z), (13.0, -12.0, 13.0, CORREDOR_Z),
]

TRILHAS: list[list[P]] = [
    [INICIO, (0.0, 26.0), (0.0, 14.0), (0.0, 0.0), (0.0, -3.5), (0.0, -13.0), (0.0, -22.0), SANTUARIO],
    [(0.0, 14.0), (-10.0, 15.0), (-17.5, 16.0)], [(0.0, 14.0), (10.0, 15.0), (17.0, 16.0)],
    [(0.0, 26.0), (11.0, 27.0), (19.0, 27.0)], [(0.0, 26.0), (-11.0, 27.0), (-18.0, 27.0)],
    [(0.0, 0.0), (-20.0, 0.0), (-29.0, 0.0), (-29.0, -15.0), (-10.0, -18.0), (0.0, -18.0)],
    [(0.0, 0.0), (20.0, 0.0), (29.0, 0.0), (29.0, -15.0), (10.0, -18.0), (0.0, -18.0)],
    [(-24.0, -3.5), (24.0, -3.5)],  # o corredor
]
MARCOS: dict[str, P] = {
    "sapateira": (0.0, -7.5), "enfermaria": (-19.5, -8.5), "sala": (8.5, -8.5), "musica": (19.5, -8.5),
    "ginasio": (-17.5, 16.0), "piscina": (17.0, 16.0), "coelheira": (19.0, 27.0),
}
NOME_MARCO = {"sapateira": "a sapateira", "enfermaria": "a enfermaria", "sala": "a sala 2-1",
              "musica": "a sala de musica", "ginasio": "o ginasio", "piscina": "a piscina vazia",
              "coelheira": "a coelheira"}
AMULETO_NO_MARCO = {"sapateira": (2.0, -0.6, 1.3), "enfermaria": (-3.0, 1.6, 0.6), "sala": (0.0, -2.2, 0.85),
                    "musica": (2.0, -1.6, 1.0), "ginasio": (-0.8, 1.6, 0.5), "piscina": (1.2, -2.2, 0.4),
                    "coelheira": (0.8, -0.8, 0.9)}
ESCONDERIJOS = {
    "no armario de limpeza": (-24.6, -3.5, 1.0, "seco"),
    "embaixo da mesa do professor": (-8.5, -10.4, 0.4, "seco"),
    "atras do piano": (25.3, -11.3, 0.9, "seco"),
}
HISTORIA = "Sexta noite. A escola. Ela tem medo do escuro: vem para a luz."
TEXTOS = {
    "sapateira": "Fileira tres, o ultimo escaninho. Os sapatos dela ainda estao aqui. Ninguem tirou.",
    "enfermaria": "Ela tem medo do escuro. Com a lanterna acesa, ela vem. Com a luz nela, ela vem correndo.",
    "sala": "Desenho na parede: a turma toda de maos dadas. Ela, sozinha, no canto. Embaixo: 'quem me procura?'",
    "musica": "A escola e dela. Ela passa pelas paredes. Escute: quando ela anda, as juntas estalam.",
    "ginasio": "Apague a luz e ela para. Mas no escuro voce tambem nao ve nada.",
    "piscina": "Acharam a lanterna dela no fundo da piscina vazia. Ela, nao. Ninguem procurou mais.",
    "coelheira": "Ela cuidava dos coelhos. Quando ela sumiu, ninguem deu comida para eles.",
}
BILHETE_INICIO = "ESCOLA PRIMARIA DA ALDEIA -- FECHADA."
GINASIO = (-32.0, 10.0, -19.5, 22.0)
PISCINA = (19.5, 11.5, 30.0, 20.5)
PEQUENA_APARECE = 1  # aqui ela aparece no primeiro omamori


def dist_trilha(x: float, z: float) -> float:
    return min(dist_segmento((x, z), t[i], t[i + 1]) for t in TRILHAS for i in range(len(t) - 1))


def no_predio(x: float, z: float, folga: float = 0.0) -> bool:
    x0, z0, x1, z1 = PREDIO
    return x0 - folga < x < x1 + folga and z0 - folga < z < z1 + folga


def _dentro(caixa, x, z, folga=0.0) -> bool:
    return caixa[0] - folga < x < caixa[2] + folga and caixa[1] - folga < z < caixa[3] + folga


def gerar_mapa(semente: int = 31) -> Mapa:
    rng = random.Random(semente)
    m = Mapa(bioma="escola", nome="a escola", historia=HISTORIA, inicio=INICIO, santuario=SANTUARIO,
             limite=LIMITE, marcos=dict(MARCOS), nome_marco=dict(NOME_MARCO), trilhas=TRILHAS,
             esconderijos=dict(ESCONDERIJOS), altar_oitavo=ALTAR_OITAVO, amuleto_no_marco=dict(AMULETO_NO_MARCO),
             tem_vulto=False, tem_pequena=True, pequena_aparece=PEQUENA_APARECE,
             nevoa=(10 / 255, 10 / 255, 14 / 255), neblina_longe=16.0)
    for nome, (mx, mz) in MARCOS.items():
        dx, dz, y = AMULETO_NO_MARCO[nome]
        m.amuletos.append((mx + dx, mz + dz, y))
    _colisao(m)
    for _ in range(1400):  # as arvores: uma parede em volta e algumas no patio dos fundos
        x, z = rng.uniform(-TAMANHO - 4, TAMANHO + 4), rng.uniform(-TAMANHO - 4, TAMANHO + 4)
        dentro = abs(x) < LIMITE + 1 and abs(z) < LIMITE + 1
        if dentro:
            fundos = z < -15.0 and dist_trilha(x, z) > 2.5 and math.hypot(x - SANTUARIO[0], z - SANTUARIO[1]) > 6
            if not fundos or rng.random() > 0.08:
                continue
        m.arvores.append((x, z, rng.uniform(7.0, 11.0), False))
        if dentro:
            m.circulos.append((x, z, 0.35))
    m.armadilhas = [(-8.0, 20.5), (9.0, 7.0), (-21.0, -16.4)]  # cacos e pregos no chao, la fora
    m.pilhas = [(-1.5, 22.0), (-22.0, -3.5), (10.0, -3.5), (-8.5, -6.4), (24.0, 25.0), (-27.5, -8.0)]
    m.bilhetes = [(INICIO[0] + 1.5, INICIO[1] - 0.6, 0.0, BILHETE_INICIO)]
    lugar = {"sapateira": (-1.2, -9.6), "enfermaria": (-21.5, -6.0), "sala": (6.0, -6.2), "musica": (16.0, -6.4),
             "ginasio": (-17.0, 13.6), "piscina": (17.6, 13.0), "coelheira": (17.0, 26.0)}
    m.bilhetes += [(*lugar[k], 0.0, t) for k, t in TEXTOS.items()]
    m.luzes = [((0.0, 2.6, -3.4), (0.15, 0.7, 0.25), 3.5),  # a placa de saida, verde, no corredor
               ((-19.5, 2.4, -9.0), (0.7, 0.75, 0.9), 2.8),  # a lampada da enfermaria, quase morta
               ((-17.5, 2.6, 15.4), (1.0, 0.7, 0.35), 3.5),  # a lampada da porta do ginasio
               ((-1.0, 1.0, -31.6), (1.5, 0.3, 0.15), 3.0)]  # o santuario
    m.montar_grade()
    return m


def _colisao(m: Mapa) -> None:
    e = PAREDE / 2
    for x0, z0, x1, z1 in PAREDES:
        m.caixas.append((min(x0, x1) - e, min(z0, z1) - e, max(x0, x1) + e, max(z0, z1) + e))
    m.caixas += [(-3.6, -9.5, -1.8, -6.0), (1.8, -9.5, 3.6, -6.0)]  # as sapateiras, dos dois lados do saguao
    m.caixas += [(-33.5, 30.3, -2.5, 30.7), (2.5, 30.3, 33.5, 30.7)]  # o muro baixo (o portao no meio)
    for cx, cz in _carteiras():
        m.circulos.append((cx, cz, 0.38))
    m.caixas += [(-9.6, -11.4, -7.4, -10.9), (7.4, -11.4, 9.6, -10.9)]  # as mesas do professor
    m.caixas.append((-23.5, -11.6, -21.5, -10.4))  # a cama da enfermaria
    m.caixas.append((-17.5, -11.6, -15.5, -10.4))
    m.caixas.append((21.6, -11.8, 24.4, -11.2))  # o piano
    m.caixas.append(GINASIO)
    m.caixas.append(PISCINA)
    cx, cz = MARCOS["coelheira"]
    m.caixas.append((cx + 1.0, cz - 2.2, cx + 3.4, cz + 0.6))
    m.circulos += [(-21.0, 28.4, 0.2), (-17.0, 28.4, 0.2)]  # o balanco
    sx, sz = SANTUARIO
    m.caixas.append((sx - 1.0, sz - 4.0, sx + 1.0, sz - 2.6))
    m.circulos += [(sx - 1.3, sz + 1.5, 0.3), (sx + 1.3, sz + 1.5, 0.3)]


def _carteiras() -> list[P]:
    """As carteiras das duas salas de aula (a 2-1 e a do lado do saguao): 4 fileiras de 3."""
    lugares = []
    for cx in (-8.5, 8.5):
        for i in range(3):
            for j in range(3):
                x, z = cx - 2.4 + i * 2.4, -9.6 + j * 1.6
                if (i, j) == (1, 2) or (cx > 0 and (i, j) == (2, 1)):
                    continue  # o caminho da porta; e a carteira dela, que tiraram
                lugares.append((x, z))
    return lugares


# ------------------------------------------------------------------ geometria

TABUA, TABUA_CLARA, VIDRO, LOUSA = (92, 70, 52), (120, 96, 70), (16, 20, 26), (30, 52, 40)


def _parede(x0, z0, x1, z1, base=0.0, topo=ALTO, cor=TABUA) -> list[Tri]:
    e = PAREDE
    return bloco(((x0 + x1) / 2, base, (z0 + z1) / 2), topo, abs(x1 - x0) + e, abs(x1 - x0) + e,
                 abs(z1 - z0) + e, cor)


def _predio() -> list[Tri]:
    t: list[Tri] = []
    for x0, z0, x1, z1 in PAREDES:
        t += _parede(x0, z0, x1, z1)
    x0, z0, x1, z1 = PREDIO
    t += bloco(((x0 + x1) / 2, ALTO, (z0 + z1) / 2), ALTO + 0.25, x1 - x0 + 0.6, x1 - x0 + 0.6, z1 - z0 + 0.6,
               (40, 34, 30))  # o teto do terreo (e o chao do andar de cima)
    for zz in (z0, z1):  # o andar de cima, so por fora: as paredes e as janelas escuras
        t += _parede(x0, zz, x1, zz, ALTO + 0.25, 6.0, TABUA_CLARA)
    for xx in (x0, x1):
        t += _parede(xx, z0, xx, z1, ALTO + 0.25, 6.0, TABUA_CLARA)
    t += bloco((0.0, 6.0, (z0 + z1) / 2), 7.2, x1 - x0 + 1.6, x1 - x0 - 2.0, z1 - z0 + 1.6, (44, 46, 52))  # o telhado
    for k in range(12):  # as janelas da frente, nos dois andares
        x = x0 + 2.2 + k * 4.3
        if all(abs(x - p) > 2.2 for p in (-20.0, 0.0, 20.0)):  # nao em cima das portas
            t += bloco((x, 1.1, z1), 2.3, 2.2, 2.2, PAREDE + 0.06, VIDRO)
        t += bloco((x, 4.0, z1), 5.3, 2.2, 2.2, PAREDE + 0.06, VIDRO)
    t += bloco((0.0, 6.2, z1 + 0.25), 7.0, 1.4, 1.4, 0.2, (210, 206, 196))  # o relogio parado
    t += bloco((0.0, 6.6, z1 + 0.37), 6.62, 0.05, 0.05, 0.04, (20, 20, 20), 0.8, (0.0, 6.6, z1 + 0.37))
    return t


def _salas() -> list[Tri]:
    t: list[Tri] = []
    for cx, cz in _carteiras():
        t += bloco((cx, 0, cz), 0.7, 0.6, 0.6, 0.45, TABUA_CLARA)
        t += bloco((cx, 0, cz + 0.45), 0.42, 0.36, 0.36, 0.34, MADEIRA_ESCURA)  # a cadeira
    for cx in (-8.5, 8.5):  # a lousa e a mesa do professor
        t += bloco((cx, 0.9, -11.82), 2.3, 4.0, 4.0, 0.06, LOUSA)
        t += bloco((cx, 0, -11.15), 0.78, 2.2, 2.2, 0.5, MADEIRA)
    t += bloco((8.5, 1.4, -11.78), 1.5, 0.9, 0.9, 0.03, (220, 220, 210))  # giz: "quem me procura?"
    for k in range(7):  # os desenhos na parede do corredor da 2-1
        t += bloco((5.0 + k * 0.6, 1.3, -5.2), 1.75, 0.45, 0.45, 0.03, (200 - k * 9, 190, 170 + k * 6))
    t += bloco((9.2, 1.3, -5.2), 1.75, 0.45, 0.45, 0.03, (120, 40, 40))  # o dela, com o resto em branco
    for bx in (-22.5, -16.5):  # a enfermaria: as camas e a cortina
        t += bloco((bx, 0, -11.0), 0.55, 2.0, 2.0, 1.2, (200, 200, 196))
        t += bloco((bx + 1.3, 0, -10.4), 2.2, 0.04, 0.04, 2.4, (170, 190, 186))
    t += bloco((-19.5, 2.55, -9.0), 2.62, 0.4, 0.4, 0.15, (160, 170, 190), emissivo=True)  # a lampada fraca
    t += bloco((23.0, 0, -11.5), 1.1, 2.8, 2.8, 0.6, (12, 12, 14))  # o piano
    t += bloco((23.0, 1.1, -11.7), 1.6, 2.6, 2.6, 0.12, (12, 12, 14))
    t += bloco((23.0, 0.8, -11.18), 0.84, 2.4, 2.4, 0.12, (220, 216, 206))  # as teclas
    for lado in (-1, 1):  # as sapateiras do saguao
        x = lado * 2.7
        t += bloco((x, 0, -7.75), 1.8, 1.8, 1.8, 3.5, (110, 90, 66))
        for j in range(5):
            for k in range(4):
                t += bloco((x - lado * 0.92, 0.2 + k * 0.4, -9.2 + j * 0.7), 0.5 + k * 0.4, 0.04, 0.04, 0.6,
                           (40, 30, 24))
    t += bloco((-24.6, 0, -2.6), 2.2, 1.0, 1.0, 0.04, MADEIRA_ESCURA)  # a porta do armario de limpeza
    t += bloco((0.0, 2.45, -2.35), 2.7, 0.8, 0.8, 0.08, (60, 220, 90), emissivo=True)  # SAIDA
    return t


def _ginasio() -> list[Tri]:
    x0, z0, x1, z1 = GINASIO
    t = bloco(((x0 + x1) / 2, 0, (z0 + z1) / 2), 6.5, x1 - x0, x1 - x0, z1 - z0, (130, 126, 118))
    t += bloco(((x0 + x1) / 2, 6.5, (z0 + z1) / 2), 8.0, x1 - x0 + 0.8, 1.0, z1 - z0 + 0.8, (60, 70, 80))
    t += bloco((x1 + 0.02, 0, 16.0), 2.4, 0.06, 0.06, 2.0, (30, 28, 26))  # a porta, trancada
    return t + bloco((x1 + 0.1, 2.5, 15.4), 2.75, 0.06, 0.06, 0.3, (255, 200, 120), emissivo=True)


def _piscina() -> list[Tri]:
    x0, z0, x1, z1 = PISCINA
    t = bloco(((x0 + x1) / 2, -0.01, (z0 + z1) / 2), 0.02, x1 - x0, x1 - x0, z1 - z0, (40, 60, 70))  # o fundo
    for a, b, c, d in ((x0, z0, x1, z0), (x0, z1, x1, z1), (x0, z0, x0, z1), (x1, z0, x1, z1)):
        t += _parede(a, b, c, d, 0.0, 0.35, (180, 186, 186))  # a borda
    t += bloco(((x0 + x1) / 2, 0.0, (z0 + z1) / 2), 0.03, x1 - x0 - 1.0, x1 - x0 - 1.0, z1 - z0 - 1.0,
               (24, 44, 52))  # o que sobrou da agua, preta
    for k in range(9):  # a cerca
        t += bloco((x0 - 0.8, 0, z0 - 0.6 + k * 1.3), 1.6, 0.06, 0.06, 0.06, (70, 74, 70))
    t += bloco((x0 - 0.8, 1.5, (z0 + z1) / 2 - 1.0), 1.56, 0.04, 0.04, 9.0, (70, 74, 70))
    return t + bloco((x0 + 1.2, 0.35, z0 + 0.6), 0.37, 0.4, 0.4, 0.15, (220, 200, 90))  # a lanterna dela, la


def _coelheira() -> list[Tri]:
    cx, cz = MARCOS["coelheira"]
    t = bloco((cx + 2.2, 0, cz - 0.8), 1.6, 2.4, 2.4, 2.8, (60, 52, 44))
    t += bloco((cx + 0.99, 0.2, cz - 0.8), 1.4, 0.04, 0.04, 2.4, (90, 96, 96))  # a tela
    return t + bloco((cx + 2.2, 1.6, cz - 0.8), 1.8, 2.8, 2.6, 3.2, (50, 42, 36))


def _balanco() -> list[Tri]:
    t = bloco((-21.0, 0, 28.4), 2.6, 0.12, 0.12, 0.12, (70, 70, 74)) + bloco((-17.0, 0, 28.4), 2.6, 0.12, 0.12,
                                                                           0.12, (70, 70, 74))
    t += bloco((-19.0, 2.5, 28.4), 2.62, 4.2, 4.2, 0.12, (70, 70, 74))
    for x in (-20.0, -18.0):
        t += bloco((x, 0.5, 28.4), 2.5, 0.02, 0.02, 0.02, (50, 50, 50))
        t += bloco((x, 0.45, 28.4), 0.52, 0.5, 0.5, 0.25, MADEIRA)
    return t


def _santuario() -> list[Tri]:
    sx, sz = SANTUARIO
    t = torii(sx, sz + 1.5, (100, 30, 26), (64, 20, 18))
    t += lanterna(sx - 1.6, sz + 0.2, (110, 108, 104), (255, 70, 40))
    t += bloco((sx, 0, sz - 3.3), 1.4, 1.8, 1.8, 1.3, MADEIRA_ESCURA)
    return t + bloco((sx, 1.4, sz - 3.3), 2.0, 2.4, 0.2, 1.9, (40, 30, 28))


def geometria(m: Mapa) -> list[Tri]:
    rng = random.Random(6)

    def cor(x, z):
        tom = rng.uniform(-4, 4)
        if no_predio(x, z):
            return (int(78 + tom), int(58 + tom), int(42 + tom))  # o assoalho
        if -2.0 < z < 30.0 and abs(x) < 34.0 and not _dentro(PISCINA, x, z):
            return (int(84 + tom), int(78 + tom), int(66 + tom))  # o patio de terra
        if dist_trilha(x, z) < 1.1:
            return (int(70 + tom), int(66 + tom), int(58 + tom))
        return (int(36 + tom), int(44 + tom), int(34 + tom))

    tris = chao(-TAMANHO - 4, TAMANHO + 4, -TAMANHO - 4, TAMANHO + 4, 1.0, cor)
    for x, z, alto, _ in m.arvores:
        tris += _pinheiro(x, z, alto, (26, 36, 30))
    tris += _predio() + _salas() + _ginasio() + _piscina() + _coelheira() + _balanco() + _santuario()
    for lado in (-1, 1):  # o portao da escola e o muro baixo
        tris += bloco((lado * 2.2, 0, 30.5), 2.0, 0.6, 0.6, 0.6, PEDRA)
        tris += bloco((lado * 18.0, 0, 30.5), 1.0, 31.0, 31.0, 0.4, PEDRA)
    tris += bloco((INICIO[0] + 1.5, 0, INICIO[1] - 1.0), 1.3, 0.1, 0.1, 0.1, MADEIRA)
    tris += bloco((INICIO[0] + 1.5, 1.0, INICIO[1] - 1.0), 1.35, 0.8, 0.8, 0.05, MADEIRA)
    for x, z, _, _ in m.bilhetes:
        tris += bloco((x, 0.02, z), 0.032, 0.22, 0.22, 0.3, (196, 188, 168))
    return tris
