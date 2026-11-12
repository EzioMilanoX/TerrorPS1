# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""A quarta noite: o bambuzal.

Trilhas estreitas num bambuzal fechado, a cabana do cortador, o forno de carvao, a cabeca
de pedra caida, a clareira das lanternas, o sino, o tumulo do cortador. Fora das trilhas, o
chao e cheio de tocos de bambu cortados em ponta: quem corta caminho se corta -- e sangra.
Aqui quem caca e o Farejador: ele so segue o seu sangue.

Mesmo contrato da floresta (`mapa.Mapa`): `gerar_mapa()` e `geometria()`.
"""
from __future__ import annotations

import math
import random

from terror_ps1.malhas import Tri, bloco, chao, cone, icosaedro, lanterna, torii
from terror_ps1.mapa import MADEIRA, MADEIRA_ESCURA, PEDRA, Mapa, P, _pinheiro, dist_segmento

TAMANHO = 40.0
LIMITE = 37.5
INICIO: P = (0.0, 34.0)
SANTUARIO: P = (0.0, -31.0)
ALTAR_OITAVO: P = (0.0, -32.8)
FAREJADOR_INICIO: P = (-26.0, -28.0)
ESPACO_BAMBU = 1.45

TRILHAS: list[list[P]] = [
    [INICIO, (3.0, 25.0), (-3.0, 15.0), (2.0, 5.0), (-3.0, -7.0), (3.0, -18.0), SANTUARIO],
    [(3.0, 25.0), (8.0, 26.0)], [(-3.0, 15.0), (-12.0, 15.0), (-19.0, 15.5)],
    [(2.0, 5.0), (12.0, 9.0), (19.0, 11.5)], [(-3.0, -7.0), (8.0, -9.0), (17.0, -10.0)],
    [(-3.0, -7.0), (-14.0, -11.0), (-21.0, -14.0)], [(3.0, -18.0), (11.0, -23.0)],
    [(3.0, -18.0), (-4.0, -22.0), (-9.0, -25.0)],
]
MARCOS: dict[str, P] = {
    "cabana": (-21.0, 16.0), "forno": (21.0, 12.0), "cabeca": (19.0, -10.0), "clareira": (-22.0, -14.0),
    "tumulo": (12.0, -24.0), "altar": (-10.0, -26.0), "sino": (9.5, 26.5),
}
NOME_MARCO = {"cabana": "a cabana do cortador", "forno": "o forno de carvao", "cabeca": "a cabeca de pedra",
              "clareira": "a clareira das lanternas", "tumulo": "o tumulo do cortador", "altar": "o altar de pedra",
              "sino": "o sino"}
AMULETO_NO_MARCO = {"cabana": (1.2, 0.0, 0.9), "forno": (0.0, 1.9, 0.6), "cabeca": (-2.2, 0.0, 0.5),
                    "clareira": (0.0, 0.0, 1.0), "tumulo": (0.0, 1.2, 0.6), "altar": (0.0, 0.0, 0.9),
                    "sino": (0.0, 0.0, 0.6)}
RAIO_MARCO = {"cabana": 5.0, "forno": 4.0, "cabeca": 4.5, "clareira": 6.0, "tumulo": 3.0, "altar": 3.0, "sino": 3.0}
ESCONDERIJOS = {
    "dentro do forno de carvao": (21.0, 12.0, 0.8, "seco"),
    "embaixo da cabana do cortador": (-21.0, 17.4, 0.3, "seco"),
    "no oco da cabeca de pedra": (19.6, -10.6, 0.9, "seco"),
}
HISTORIA = "Quarta noite. O bambuzal. Nao corte caminho: o chao corta -- e o que vem depois so quer sangue."
TEXTOS = {
    "cabana": "O cortador de bambu se cortou no toco e nao parou de sangrar. Tres dias depois acharam a trilha "
              "dele. Lambida. Ate o fim.",
    "forno": "Ele nao ve e nao ouve. So cheira. E so o sangue.",
    "cabeca": "Fora da trilha o chao e cheio de tocos em ponta. Agachado da para sentir com o pe antes de pisar.",
    "clareira": "Ele segue as gotas na ordem em que cairam. Sempre. Mesmo que voce esteja do lado.",
    "tumulo": "Quando o sangue para, ele se perde. Ate a proxima gota.",
    "altar": "Escondido nao adianta se o rastro leva ate a porta.",
    "sino": "Toquei o sino para chamar ajuda. Ninguem veio. Mas alguma coisa parou de lamber o chao para escutar.",
}
BILHETE_INICIO = "BAMBUZAL -- NAO SAIA DA TRILHA."


def dist_trilha(x: float, z: float) -> float:
    return min(dist_segmento((x, z), t[i], t[i + 1]) for t in TRILHAS for i in range(len(t) - 1))


def _livre(x: float, z: float) -> bool:
    """Longe das trilhas, dos lugares e do comeco/fim."""
    if dist_trilha(x, z) < 1.7:
        return False
    if math.hypot(x - INICIO[0], z - INICIO[1]) < 5.0 or math.hypot(x - SANTUARIO[0], z - SANTUARIO[1]) < 6.0:
        return False
    return all(math.hypot(x - mx, z - mz) > RAIO_MARCO[k] for k, (mx, mz) in MARCOS.items())


def gerar_mapa(semente: int = 17) -> Mapa:
    rng = random.Random(semente)
    m = Mapa(bioma="bambuzal", nome="o bambuzal", historia=HISTORIA, inicio=INICIO, santuario=SANTUARIO,
             limite=LIMITE, marcos=dict(MARCOS), nome_marco=dict(NOME_MARCO), trilhas=TRILHAS,
             esconderijos=dict(ESCONDERIJOS), altar_oitavo=ALTAR_OITAVO, amuleto_no_marco=dict(AMULETO_NO_MARCO),
             tem_vulto=False, tem_pequena=False, tem_farejador=True, farejador_inicio=FAREJADOR_INICIO,
             nevoa=(24 / 255, 30 / 255, 26 / 255), neblina_longe=19.0)
    for nome, (mx, mz) in MARCOS.items():
        dx, dz, y = AMULETO_NO_MARCO[nome]
        m.amuletos.append((mx + dx, mz + dz, y))
    _colisao(m)
    ocupado: dict[tuple[int, int], list[P]] = {}
    for _ in range(9000):  # o bambu: fechado fora das trilhas (e uma parede alem do limite)
        x, z = rng.uniform(-TAMANHO - 4, TAMANHO + 4), rng.uniform(-TAMANHO - 4, TAMANHO + 4)
        dentro = abs(x) < LIMITE + 1 and abs(z) < LIMITE + 1
        if dentro and not _livre(x, z):
            continue
        cel = (int(x // 3), int(z // 3))
        viz = [p for i in (-1, 0, 1) for j in (-1, 0, 1) for p in ocupado.get((cel[0] + i, cel[1] + j), ())]
        if any(math.hypot(x - a, z - b) < (ESPACO_BAMBU if dentro else 0.9) for a, b in viz):
            continue
        ocupado.setdefault(cel, []).append((x, z))
        m.arvores.append((x, z, rng.uniform(7.0, 11.0), False))
        m.circulos.append((x, z, 0.09))
    while len(m.tocos) < 260:  # tocos em ponta: perto das trilhas (onde da vontade de cortar caminho)
        x, z = rng.uniform(-LIMITE, LIMITE), rng.uniform(-LIMITE, LIMITE)
        d = dist_trilha(x, z)
        if 1.5 < d < 7.0 and _livre(x, z) and all(math.hypot(x - a, z - b) > 0.6 for a, b in m.tocos[-40:]):
            m.tocos.append((x, z))
    pontos = TRILHAS
    while len(m.armadilhas) < 6:
        t = rng.choice(pontos)
        i = rng.randrange(len(t) - 1)
        k = rng.random()
        x = t[i][0] + (t[i + 1][0] - t[i][0]) * k
        z = t[i][1] + (t[i + 1][1] - t[i][1]) * k
        longe = [INICIO, SANTUARIO, *MARCOS.values()] + m.armadilhas
        if all(math.hypot(x - p[0], z - p[1]) > 5.0 for p in longe):
            m.armadilhas.append((x, z))
    m.pilhas = [(4.2, 20.0), (-6.0, 15.6), (9.0, 8.2), (-10.0, -10.4), (6.0, -21.0)]
    m.bilhetes = [(INICIO[0] + 1.5, INICIO[1] - 0.6, 0.0, BILHETE_INICIO)]
    lugar = {"cabana": (-18.6, 15.0), "forno": (18.6, 11.4), "cabeca": (16.6, -9.6), "clareira": (-19.6, -13.4),
             "tumulo": (10.6, -22.6), "altar": (-8.4, -24.6), "sino": (7.6, 25.4)}
    m.bilhetes += [(*lugar[k], 0.0, t) for k, t in TEXTOS.items()]
    cx, cz = MARCOS["clareira"]
    m.luzes = [((-21.0, 1.6, 16.0), (1.1, 0.6, 0.3), 4.5),  # a cabana
               ((21.0, 0.6, 12.0), (1.4, 0.4, 0.1), 3.5),  # as brasas do forno
               ((cx - 2.0, 2.4, cz), (1.0, 0.75, 0.4), 4.0), ((cx + 2.0, 2.4, cz + 1.0), (1.0, 0.75, 0.4), 4.0),
               ((12.0, 0.5, -23.4), (1.0, 0.8, 0.4), 2.8),  # a vela do tumulo
               ((-1.0, 1.0, -31.6), (1.5, 0.3, 0.15), 3.0)]  # o santuario
    m.montar_grade()
    return m


def _colisao(m: Mapa) -> None:
    cx, cz = MARCOS["cabana"]  # a cabana do cortador, sobre estacas: so a parede de tras e os lados
    m.caixas += [(cx - 2.2, cz + 1.6, cx + 2.2, cz + 1.8), (cx - 2.2, cz - 1.0, cx - 2.0, cz + 1.8)]
    fx, fz = MARCOS["forno"]
    m.circulos.append((fx, fz, 1.3))
    hx, hz = MARCOS["cabeca"]
    m.circulos.append((hx, hz, 1.8))
    tx, tz = MARCOS["tumulo"]
    m.circulos.append((tx, tz, 0.5))
    sx, sz = MARCOS["sino"]
    m.circulos += [(sx - 1.0, sz, 0.15), (sx + 1.0, sz, 0.15)]
    sx, sz = SANTUARIO
    m.caixas.append((sx - 1.0, sz - 4.0, sx + 1.0, sz - 2.6))
    m.circulos += [(sx - 1.3, sz + 1.5, 0.3), (sx + 1.3, sz + 1.5, 0.3)]


# ------------------------------------------------------------------ geometria

VERDE_BAMBU, FOLHA = (92, 118, 70), (54, 78, 46)


def _bambu(x, z, alto, rng) -> list[Tri]:
    t = bloco((x, 0, z), alto, 0.12, 0.09, 0.12, VERDE_BAMBU)
    for k in range(1, int(alto / 1.6)):  # os nos do bambu
        y = k * 1.6
        t += bloco((x, y, z), y + 0.05, 0.14, 0.14, 0.14, (70, 92, 54))
    for k in range(3):  # tufos de folha la em cima
        y = alto - 0.8 - k * 1.1
        t += cone((x + rng.uniform(-0.3, 0.3), y, z + rng.uniform(-0.3, 0.3)), 0.7, 0.9, FOLHA, lados=4)
    return t


def malha_toco() -> list[Tri]:
    """Um toco de bambu cortado em ponta (centrado na origem)."""
    t = bloco((0, 0, 0), 0.28, 0.1, 0.1, 0.1, VERDE_BAMBU)
    return t + bloco((0, 0.28, 0), 0.42, 0.1, 0.01, 0.1, (150, 160, 110), 0.5, (0, 0.28, 0))  # a ponta


_TOCO = malha_toco()


def _cabana(x, z) -> list[Tri]:
    t: list[Tri] = []
    for dx in (-2.0, 2.0):
        for dz in (-1.6, 1.6):
            t += bloco((x + dx, 0, z + dz), 0.8, 0.15, 0.15, 0.15, MADEIRA_ESCURA)  # as estacas
    t += bloco((x, 0.8, z), 0.95, 4.4, 4.4, 3.6, MADEIRA)  # o assoalho
    t += bloco((x, 0.95, z + 1.7), 3.0, 4.4, 4.4, 0.2, MADEIRA_ESCURA)
    t += bloco((x - 2.1, 0.95, z), 3.0, 0.2, 0.2, 3.6, MADEIRA_ESCURA)
    t += bloco((x, 3.0, z), 3.9, 5.0, 0.3, 4.4, (60, 52, 40))
    for k in range(5):  # feixes de bambu cortado encostados
        t += bloco((x + 1.0 + k * 0.15, 0.95, z + 1.4), 3.2, 0.08, 0.06, 0.08, VERDE_BAMBU, -0.15, (x, 0.95, z))
    t += bloco((x + 1.2, 0.95, z), 1.45, 0.4, 0.4, 0.4, MADEIRA)  # o cepo onde o amuleto fica
    return t + bloco((x, 1.4, z + 1.2), 1.6, 0.08, 0.06, 0.08, (230, 170, 90), emissivo=True)


def _forno(x, z) -> list[Tri]:
    domo = icosaedro((x, 0.0, z), 1.4, (86, 74, 66), sub=1)
    t = [tuple((p[0], max(0.0, p[1]) * 0.9, p[2]) for p in tri[:3]) + tri[3:] for tri in domo]
    t += bloco((x, 0, z + 1.35), 0.7, 0.7, 0.7, 0.1, (12, 8, 8))  # a boca escura
    t += icosaedro((x, 0.12, z + 1.0), 0.18, (220, 80, 20), emissivo=True)  # brasas
    return t + bloco((x, 1.2, z - 0.3), 2.2, 0.3, 0.25, 0.3, (70, 62, 56))  # a chamine


def _cabeca(x, z) -> list[Tri]:
    cab = icosaedro((x, 1.2, z), 1.8, (110, 108, 100), sub=1)
    t = [tuple((p[0], p[1], p[2]) for p in tri[:3]) + tri[3:] for tri in cab]
    for dx in (-0.6, 0.6):  # os olhos fechados, de lado
        t += bloco((x - 1.75, 1.6 + dx * 0.3, z + dx), 1.65 + dx * 0.3, 0.05, 0.05, 0.5, (40, 38, 36))
    return t + bloco((x - 1.7, 0.5, z), 0.6, 0.1, 0.1, 0.9, (40, 38, 36))  # a boca


def _clareira(x, z) -> list[Tri]:
    t: list[Tri] = []
    for dx, dz in ((-2.0, 0.0), (2.0, 1.0), (0.0, -2.0)):  # postes com lanternas penduradas
        t += bloco((x + dx, 0, z + dz), 2.6, 0.1, 0.1, 0.1, MADEIRA_ESCURA)
        t += icosaedro((x + dx, 2.4, z + dz), 0.22, (240, 200, 130), emissivo=True)
    return t + bloco((x, 0, z), 0.9, 0.6, 0.5, 0.6, PEDRA)  # a pedra do amuleto


def _tumulo(x, z) -> list[Tri]:
    t = bloco((x, 0, z), 1.1, 0.5, 0.4, 0.2, PEDRA)
    t += bloco((x, 0, z + 0.6), 0.12, 1.0, 1.0, 1.6, (60, 52, 44))
    for k in range(4):  # bambu cortado fincado em volta
        a = k * math.pi / 2 + 0.4
        t += bloco((x + 1.1 * math.cos(a), 0, z + 1.1 * math.sin(a)), 0.9, 0.08, 0.06, 0.08, VERDE_BAMBU)
    return t + bloco((x, 0.4, z + 0.6), 0.55, 0.05, 0.05, 0.05, (240, 220, 160), emissivo=True)


def _altar(x, z) -> list[Tri]:
    return bloco((x, 0, z), 0.85, 1.6, 1.4, 1.0, PEDRA) + bloco((x, 0.85, z), 0.95, 1.8, 1.8, 1.2, (90, 88, 84))


def _sino(x, z) -> list[Tri]:
    t = bloco((x - 1.0, 0, z), 2.6, 0.14, 0.12, 0.14, MADEIRA_ESCURA) + bloco((x + 1.0, 0, z), 2.6, 0.14, 0.12, 0.14,
                                                                               MADEIRA_ESCURA)
    t += bloco((x, 2.5, z), 2.7, 2.4, 2.4, 0.16, MADEIRA)
    sino = icosaedro((x, 1.8, z), 0.45, (90, 74, 40), sub=1)
    return t + [tuple((p[0], min(p[1], 2.2), p[2]) for p in tri[:3]) + tri[3:] for tri in sino]


def _santuario() -> list[Tri]:
    sx, sz = SANTUARIO
    t = torii(sx, sz + 1.5, (100, 30, 26), (64, 20, 18))
    t += lanterna(sx - 1.6, sz + 0.2, (110, 108, 104), (255, 70, 40))
    t += bloco((sx, 0, sz - 3.3), 1.4, 1.8, 1.8, 1.3, MADEIRA_ESCURA)
    return t + bloco((sx, 1.4, sz - 3.3), 2.0, 2.4, 0.2, 1.9, (40, 30, 28))


def geometria(m: Mapa) -> list[Tri]:
    rng = random.Random(3)

    def cor(x, z):
        tom = rng.uniform(-5, 5)
        if dist_trilha(x, z) < 1.1:
            return (int(70 + tom), int(62 + tom), int(50 + tom))  # a trilha batida
        if rng.random() < 0.35:
            return (int(70 + tom), int(66 + tom), int(42 + tom))  # folhas secas de bambu
        return (int(44 + tom), int(50 + tom), int(36 + tom))

    tris = chao(-TAMANHO - 4, TAMANHO + 4, -TAMANHO - 4, TAMANHO + 4, 0.8, cor)
    rb = random.Random(7)
    for x, z, alto, _ in m.arvores:
        dentro = abs(x) < LIMITE + 1 and abs(z) < LIMITE + 1
        tris += _bambu(x, z, alto, rb) if dentro else _pinheiro(x, z, alto, (30, 44, 34))
    for x, z in m.tocos:
        tris += [tuple((p[0] + x, p[1], p[2] + z) for p in tri[:3]) + tri[3:] for tri in _TOCO]
    for nome, f in (("cabana", _cabana), ("forno", _forno), ("cabeca", _cabeca), ("clareira", _clareira),
                    ("tumulo", _tumulo), ("altar", _altar), ("sino", _sino)):
        tris += f(*MARCOS[nome])
    tris += _santuario()
    tris += bloco((INICIO[0] + 1.5, 0, INICIO[1] - 1.0), 1.3, 0.1, 0.1, 0.1, MADEIRA)
    tris += bloco((INICIO[0] + 1.5, 1.0, INICIO[1] - 1.0), 1.35, 0.8, 0.8, 0.05, MADEIRA)
    for x, z, _, _ in m.bilhetes:
        tris += bloco((x, 0.02, z), 0.032, 0.22, 0.22, 0.3, (196, 188, 168))
    return tris


def malha_farejador() -> list[Tri]:
    """O Farejador: comprido, de quatro, o pescoco esticado e a cabeca rente ao chao, sem olhos,
    so um focinho largo e a boca aberta. Olha para +z."""
    pele, escuro = (112, 70, 62), (24, 10, 10)
    t = bloco((0, 0.55, -0.3), 0.95, 0.55, 0.45, 1.6, pele)  # o corpo
    for dx in (-0.24, 0.24):
        for dz in (-0.9, 0.4):
            t += bloco((dx, 0, dz), 0.65, 0.09, 0.11, 0.09, pele)  # as pernas magras
    t += bloco((0, 0.35, 0.55), 0.7, 0.2, 0.16, 0.7, pele, 0.0)  # o pescoco descendo
    cabeca = icosaedro((0, 0.25, 1.05), 0.2, pele)
    t += [tuple((p[0], p[1], p[2] * 1.0 + (p[2] - 1.05) * 0.6) for p in tri[:3]) + tri[3:] for tri in cabeca]
    t += bloco((0, 0.08, 1.3), 0.22, 0.24, 0.24, 0.1, escuro)  # a boca, aberta para o chao
    return t
