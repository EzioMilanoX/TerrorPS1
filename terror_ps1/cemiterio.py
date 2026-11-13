# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""A quinta noite: o cemiterio do templo.

Fileiras de tumulos de pedra e tabuas de madeira, o portao, o crematorio, a casa do zelador,
o salgueiro, o poco, o tumulo dos Mori, o ossuario. Nao ha onde se esconder: quem caca aqui
ja sabe onde voce esta. E o Fantoche -- uma mulher de luto que nao anda: e andada, pela coisa
agarrada nas costas dela. Ela so cai quando a luz pega a coisa.

Mesmo contrato da floresta (`mapa.Mapa`): `gerar_mapa()` e `geometria()`.
"""
from __future__ import annotations

import math
import random

from terror_ps1.malhas import Tri, bloco, chao, icosaedro, lanterna, torii
from terror_ps1.mapa import MADEIRA, MADEIRA_ESCURA, PEDRA, Mapa, P, _pinheiro, dist_segmento

TAMANHO = 40.0
LIMITE = 37.5
INICIO: P = (0.0, 34.0)
SANTUARIO: P = (0.0, -31.0)
ALTAR_OITAVO: P = (0.0, -32.8)
FANTOCHE_INICIO: P = (-19.0, 3.0)  # deitada na porta do crematorio, ate voce pegar o primeiro omamori

TRILHAS: list[list[P]] = [
    [INICIO, (0.0, 22.0), (0.0, 8.0), (0.0, -6.0), (0.0, -20.0), SANTUARIO],
    [(0.0, 22.0), (-12.0, 22.0), (-22.0, 22.0)], [(0.0, 22.0), (12.0, 22.0), (21.0, 23.0)],
    [(0.0, 8.0), (-10.0, 6.0), (-17.0, 4.0)], [(0.0, 8.0), (11.0, 8.0), (20.0, 7.0)],
    [(0.0, -6.0), (-12.0, -8.0), (-22.0, -10.0)], [(0.0, -6.0), (10.0, -9.0), (18.0, -14.0)],
    [(0.0, -20.0), (-9.0, -22.0)],
]
MARCOS: dict[str, P] = {
    "portao": (-23.0, 23.0), "crematorio": (-20.0, 4.0), "zelador": (22.0, 24.0), "salgueiro": (21.0, 7.0),
    "poco": (-23.0, -10.0), "mori": (19.0, -15.0), "ossuario": (-11.0, -23.0),
}
NOME_MARCO = {"portao": "o portao velho", "crematorio": "o crematorio", "zelador": "a casa do zelador",
              "salgueiro": "o salgueiro", "poco": "o poco", "mori": "o tumulo dos Mori", "ossuario": "o ossuario"}
AMULETO_NO_MARCO = {"portao": (0.0, 0.0, 1.0), "crematorio": (2.0, 0.0, 0.6), "zelador": (-1.4, 0.0, 0.9),
                    "salgueiro": (-1.2, 0.0, 0.5), "poco": (1.5, 0.0, 0.8), "mori": (-1.3, 0.0, 1.1),
                    "ossuario": (1.6, 0.0, 0.7)}
RAIO_MARCO = {"portao": 4.0, "crematorio": 5.0, "zelador": 5.0, "salgueiro": 4.5, "poco": 3.0, "mori": 3.5,
              "ossuario": 4.0}
HISTORIA = "Quinta noite. O cemiterio do templo. Aqui nao ha onde se esconder."
TEXTOS = {
    "portao": "Ela nao anda. E andada. O que anda e a coisa agarrada nas costas dela.",
    "crematorio": "Ela ja sabe onde voce esta. Sempre. Nao adianta se esconder: adianta dar a volta.",
    "zelador": "A coisa so solta quando a luz pega nela. Nas costas. De frente, a luz bate no rosto da morta, "
               "e a morta nao sente nada.",
    "salgueiro": "Ela vira devagar. Quem passa correndo do lado dela fica atras.",
    "poco": "Se ela te agarrar: segure abaixado, e depois chute, chute, chute.",
    "mori": "No tumulo da familia Mori ha cinco nomes. Um deles ainda nao tem data.",
    "ossuario": "Caida, ela fica um tempo no chao. Depois a coisa a levanta de novo.",
}
BILHETE_INICIO = "CEMITERIO -- QUEM ENTRA NAO SAI ANTES DO AMANHECER."
ESPACO_TUMULO = (2.4, 3.0)  # as fileiras: entre um tumulo e outro, entre uma fileira e outra


def dist_trilha(x: float, z: float) -> float:
    return min(dist_segmento((x, z), t[i], t[i + 1]) for t in TRILHAS for i in range(len(t) - 1))


def _livre(x: float, z: float) -> bool:
    """Longe das trilhas, dos lugares e do comeco/fim."""
    if dist_trilha(x, z) < 1.8:
        return False
    if math.hypot(x - INICIO[0], z - INICIO[1]) < 5.0 or math.hypot(x - SANTUARIO[0], z - SANTUARIO[1]) < 6.0:
        return False
    return all(math.hypot(x - mx, z - mz) > RAIO_MARCO[k] for k, (mx, mz) in MARCOS.items())


def gerar_mapa(semente: int = 23) -> Mapa:
    rng = random.Random(semente)
    m = Mapa(bioma="cemiterio", nome="o cemiterio do templo", historia=HISTORIA, inicio=INICIO, santuario=SANTUARIO,
             limite=LIMITE, marcos=dict(MARCOS), nome_marco=dict(NOME_MARCO), trilhas=TRILHAS, esconderijos={},
             altar_oitavo=ALTAR_OITAVO, amuleto_no_marco=dict(AMULETO_NO_MARCO), tem_vulto=False, tem_pequena=False,
             tem_fantoche=True, fantoche_inicio=FANTOCHE_INICIO, nevoa=(22 / 255, 22 / 255, 27 / 255),
             neblina_longe=21.0)
    for nome, (mx, mz) in MARCOS.items():
        dx, dz, y = AMULETO_NO_MARCO[nome]
        m.amuletos.append((mx + dx, mz + dz, y))
    _colisao(m)
    ex, ez = ESPACO_TUMULO
    z = -LIMITE + 1.0
    while z < LIMITE - 1.0:  # as fileiras de tumulos, com falhas (tumulos que cairam ou nunca vieram)
        x = -LIMITE + 1.0 + (0.8 if int(z) % 2 else 0.0)
        while x < LIMITE - 1.0:
            px, pz = x + rng.uniform(-0.2, 0.2), z + rng.uniform(-0.2, 0.2)
            if _livre(px, pz) and rng.random() < 0.78:
                m.pedras.append((px, pz, rng.uniform(0.9, 1.6)))  # x, z, altura do tumulo
                m.circulos.append((px, pz, 0.42))
            x += ex
        z += ez
    for _ in range(2600):  # os cedros em volta (uma parede alem do limite) e alguns entre os tumulos
        x, z = rng.uniform(-TAMANHO - 4, TAMANHO + 4), rng.uniform(-TAMANHO - 4, TAMANHO + 4)
        dentro = abs(x) < LIMITE + 1 and abs(z) < LIMITE + 1
        if dentro and (rng.random() > 0.02 or not _livre(x, z)):
            continue
        if any(math.hypot(x - a, z - b) < 1.2 for a, b, _ in m.pedras[-200:]):
            continue
        m.arvores.append((x, z, rng.uniform(8.0, 13.0), False))
        if dentro:
            m.circulos.append((x, z, 0.35))
    while len(m.armadilhas) < 5:
        t = rng.choice(TRILHAS)
        i = rng.randrange(len(t) - 1)
        k = rng.random()
        x = t[i][0] + (t[i + 1][0] - t[i][0]) * k
        z = t[i][1] + (t[i + 1][1] - t[i][1]) * k
        longe = [INICIO, SANTUARIO, *MARCOS.values()] + m.armadilhas
        if all(math.hypot(x - p[0], z - p[1]) > 5.0 for p in longe):
            m.armadilhas.append((x, z))
    m.pilhas = [(1.6, 15.0), (-7.0, 6.6), (8.0, 9.4), (-6.0, -7.4), (1.5, -14.0)]
    m.bilhetes = [(INICIO[0] + 1.5, INICIO[1] - 0.6, 0.0, BILHETE_INICIO)]
    lugar = {"portao": (-20.6, 22.0), "crematorio": (-15.6, 3.6), "zelador": (18.6, 22.6), "salgueiro": (18.0, 6.6),
             "poco": (-19.6, -9.6), "mori": (16.4, -13.4), "ossuario": (-8.4, -21.6)}
    m.bilhetes += [(*lugar[k], 0.0, t) for k, t in TEXTOS.items()]
    m.luzes = [((22.0, 1.8, 24.0), (1.1, 0.7, 0.35), 4.5),  # a janela do zelador
               ((-20.0, 0.8, 6.0), (1.3, 0.45, 0.15), 3.5),  # as brasas do crematorio
               ((19.0, 0.5, -13.6), (1.0, 0.8, 0.45), 2.6),  # o incenso no tumulo dos Mori
               ((-11.0, 1.2, -21.0), (0.6, 0.7, 1.0), 3.0),  # a lanterna do ossuario
               ((-1.0, 1.0, -31.6), (1.5, 0.3, 0.15), 3.0)]  # o santuario
    m.montar_grade()
    return m


def _colisao(m: Mapa) -> None:
    gx, gz = MARCOS["portao"]
    m.circulos += [(gx - 1.6, gz, 0.3), (gx + 1.6, gz, 0.3)]
    cx, cz = MARCOS["crematorio"]  # o forno de tijolo: a porta para a trilha
    m.caixas.append((cx - 2.5, cz - 2.0, cx + 1.0, cz + 2.0))
    zx, zz = MARCOS["zelador"]
    m.caixas.append((zx - 2.0, zz - 0.5, zx + 2.5, zz + 3.0))
    sx, sz = MARCOS["salgueiro"]
    m.circulos.append((sx, sz, 0.6))
    px, pz = MARCOS["poco"]
    m.circulos.append((px, pz, 0.9))
    mx, mz = MARCOS["mori"]
    m.circulos.append((mx, mz, 0.8))
    ox, oz = MARCOS["ossuario"]
    m.caixas.append((ox - 1.5, oz - 2.5, ox + 1.5, oz - 0.5))
    sx, sz = SANTUARIO
    m.caixas.append((sx - 1.0, sz - 4.0, sx + 1.0, sz - 2.6))
    m.circulos += [(sx - 1.3, sz + 1.5, 0.3), (sx + 1.3, sz + 1.5, 0.3)]


# ------------------------------------------------------------------ geometria

PEDRA_TUMULO, LIMO = (104, 104, 100), (70, 80, 62)


def _tumulo(x, z, alto, rng) -> list[Tri]:
    """Um tumulo japones: base larga, o pilar com o nome e, atras, tabuas de madeira finas."""
    cor = PEDRA_TUMULO if rng.random() < 0.7 else LIMO
    t = bloco((x, 0, z), 0.25, 0.8, 0.8, 0.6, (88, 88, 84))
    t += bloco((x, 0.25, z), 0.25 + alto * 0.7, 0.36, 0.34, 0.3, cor)
    for k in range(rng.randrange(0, 4)):  # as sotoba
        t += bloco((x - 0.2 + k * 0.13, 0, z + 0.4), alto + 0.7, 0.08, 0.07, 0.03, (120, 104, 80),
                   rng.uniform(-0.12, 0.12), (x, 0, z + 0.4))
    return t


def _portao(x, z) -> list[Tri]:
    t = bloco((x - 1.6, 0, z), 3.2, 0.5, 0.45, 0.5, PEDRA) + bloco((x + 1.6, 0, z), 3.2, 0.5, 0.45, 0.5, PEDRA)
    return t + bloco((x, 3.2, z), 3.5, 4.2, 4.0, 0.6, (80, 78, 74), 0.08, (x, 3.2, z))  # a viga, torta


def _crematorio(x, z) -> list[Tri]:
    t = bloco((x - 0.75, 0, z), 2.6, 3.5, 3.5, 4.0, (96, 70, 60))
    t += bloco((x - 0.75, 2.6, z), 3.0, 3.9, 3.9, 4.4, (60, 52, 50))
    t += bloco((x - 1.6, 3.0, z - 1.0), 5.5, 0.7, 0.6, 0.7, (88, 66, 58))  # a chamine
    t += bloco((x + 1.02, 0, z), 1.3, 0.05, 0.05, 1.2, (14, 10, 10))  # a boca do forno
    return t + icosaedro((x + 0.9, 0.25, z), 0.2, (220, 80, 20), emissivo=True)


def _zelador(x, z) -> list[Tri]:
    t = bloco((x + 0.25, 0, z + 1.25), 2.6, 4.5, 4.5, 3.5, MADEIRA)
    t += bloco((x + 0.25, 2.6, z + 1.25), 3.6, 5.2, 0.3, 4.2, (54, 46, 40))
    t += bloco((x - 2.02, 1.2, z + 1.8), 1.9, 0.05, 0.05, 0.8, (230, 170, 90), emissivo=True)  # a janela
    return t + bloco((x - 2.02, 0, z + 0.4), 2.0, 0.05, 0.05, 0.9, MADEIRA_ESCURA)  # a porta


def _salgueiro(x, z, rng) -> list[Tri]:
    t = bloco((x, 0, z), 3.6, 0.45, 0.3, 0.45, (58, 50, 42), 0.1, (x, 0, z))
    for k in range(26):  # os galhos caindo ate quase o chao
        a = k / 26 * 2 * math.pi
        r = rng.uniform(0.8, 2.4)
        gx, gz = x + math.cos(a) * r, z + math.sin(a) * r
        t += bloco((gx, rng.uniform(0.3, 1.2), gz), 3.8, 0.05, 0.05, 0.05, (60, 78, 52))
    return t


def _poco(x, z) -> list[Tri]:
    t = bloco((x, 0, z), 0.8, 1.6, 1.6, 1.6, PEDRA)
    t += bloco((x, 0.79, z), 0.8, 1.2, 1.2, 1.2, (8, 8, 10))  # a agua preta la embaixo
    t += bloco((x - 0.7, 0.8, z), 2.2, 0.1, 0.1, 0.1, MADEIRA_ESCURA) + bloco((x + 0.7, 0.8, z), 2.2, 0.1, 0.1, 0.1,
                                                                             MADEIRA_ESCURA)
    return t + bloco((x, 2.2, z), 2.3, 1.6, 1.6, 0.2, MADEIRA)


def _mori(x, z) -> list[Tri]:
    t = bloco((x, 0, z), 0.4, 1.8, 1.8, 1.4, (90, 90, 86))
    t += bloco((x, 0.4, z), 2.2, 0.6, 0.55, 0.45, (70, 70, 70))  # o pilar escuro da familia
    for k in range(5):  # os cinco nomes (riscos claros); o quinto, mais curto
        t += bloco((x - 0.2 + k * 0.1, 0.8, z - 0.24), 2.0 - (0.6 if k == 4 else 0.0), 0.02, 0.02, 0.01,
                   (180, 176, 160))
    return t + bloco((x - 0.5, 0.4, z - 0.6), 0.55, 0.05, 0.05, 0.05, (240, 200, 140), emissivo=True)  # o incenso


def _ossuario(x, z) -> list[Tri]:
    t = bloco((x, 0, z - 1.5), 2.2, 3.0, 2.6, 2.0, PEDRA)
    t += bloco((x, 0, z - 0.48), 1.5, 1.0, 1.0, 0.05, (12, 10, 10))  # a porta aberta
    return t + lanterna(x + 2.0, z - 0.5, (110, 108, 104), (150, 170, 255))


def _santuario() -> list[Tri]:
    sx, sz = SANTUARIO
    t = torii(sx, sz + 1.5, (100, 30, 26), (64, 20, 18))
    t += lanterna(sx - 1.6, sz + 0.2, (110, 108, 104), (255, 70, 40))
    t += bloco((sx, 0, sz - 3.3), 1.4, 1.8, 1.8, 1.3, MADEIRA_ESCURA)
    return t + bloco((sx, 1.4, sz - 3.3), 2.0, 2.4, 0.2, 1.9, (40, 30, 28))


def geometria(m: Mapa) -> list[Tri]:
    rng = random.Random(4)

    def cor(x, z):
        tom = rng.uniform(-5, 5)
        if dist_trilha(x, z) < 1.1:
            return (int(78 + tom), int(76 + tom), int(70 + tom))  # o cascalho da trilha
        return (int(40 + tom), int(46 + tom), int(36 + tom))

    tris = chao(-TAMANHO - 4, TAMANHO + 4, -TAMANHO - 4, TAMANHO + 4, 0.8, cor)
    for x, z, alto, _ in m.arvores:
        tris += _pinheiro(x, z, alto, (26, 38, 32))
    rt = random.Random(8)
    for x, z, alto in m.pedras:
        tris += _tumulo(x, z, alto, rt)
    for nome, f in (("portao", _portao), ("crematorio", _crematorio), ("zelador", _zelador), ("poco", _poco),
                    ("mori", _mori), ("ossuario", _ossuario)):
        tris += f(*MARCOS[nome])
    tris += _salgueiro(*MARCOS["salgueiro"], random.Random(2))
    tris += _santuario()
    tris += bloco((INICIO[0] + 1.5, 0, INICIO[1] - 1.0), 1.3, 0.1, 0.1, 0.1, MADEIRA)
    tris += bloco((INICIO[0] + 1.5, 1.0, INICIO[1] - 1.0), 1.35, 0.8, 0.8, 0.05, MADEIRA)
    for x, z, _, _ in m.bilhetes:
        tris += bloco((x, 0.02, z), 0.032, 0.22, 0.22, 0.3, (196, 188, 168))
    return tris


# ------------------------------------------------------------------ o Fantoche

LUTO, PELE, COISA = (18, 16, 20), (190, 176, 164), (214, 206, 190)


def malha_fantoche() -> list[Tri]:
    """O Fantoche de pe: uma mulher de quimono preto de luto, a cabeca caida de lado num angulo
    errado, os bracos soltos. Agarrada nas costas, a coisa: palida, encolhida, os dedos compridos
    passando por cima dos ombros dela. Olha para +z (as costas, e a coisa, ficam em -z)."""
    t = bloco((0, 0, 0), 1.25, 0.5, 0.36, 0.34, LUTO)  # o quimono
    t += bloco((0, 1.25, 0), 1.5, 0.36, 0.32, 0.26, LUTO)
    for dx in (-0.22, 0.22):  # os bracos, mortos
        t += bloco((dx, 0.55, 0.02), 1.42, 0.07, 0.08, 0.08, LUTO)
        t += bloco((dx, 0.42, 0.02), 0.56, 0.05, 0.05, 0.05, PELE)  # as maos
    t += bloco((0, 1.48, 0), 1.6, 0.08, 0.07, 0.08, PELE, 0.5, (0, 1.5, 0))  # o pescoco torto
    t += icosaedro((0.17, 1.62, 0.03), 0.13, PELE)  # a cabeca, caida no ombro
    t += bloco((0.17, 1.52, -0.06), 1.8, 0.28, 0.24, 0.2, (10, 8, 8), 0.5, (0.17, 1.6, 0))  # o cabelo
    t += icosaedro((0, 1.15, -0.3), 0.24, COISA)  # a coisa, encolhida nas costas
    t += icosaedro((0, 1.42, -0.28), 0.13, COISA)  # a cabeca dela, por cima do ombro
    for dx in (-0.05, 0.05):
        t += bloco((dx, 1.44, -0.16), 1.47, 0.025, 0.025, 0.02, (255, 236, 200), emissivo=True)  # os olhos
    for dx in (-0.2, 0.2):  # os dedos compridos por cima dos ombros
        t += bloco((dx, 1.45, -0.2), 1.5, 0.03, 0.03, 0.36, COISA)
        t += bloco((dx, 1.2, 0.0), 1.5, 0.03, 0.03, 0.03, COISA)
    for dx in (-0.16, 0.16):  # as pernas dela, em volta da cintura
        t += bloco((dx, 0.8, -0.26), 0.9, 0.06, 0.06, 0.3, COISA)
    return t


def malha_fantoche_caida() -> list[Tri]:
    """Caida de cara no chao (tombada para a frente, +z). A coisa continua nas costas, quieta."""
    def deitar(p):
        x, y, z = p
        return (x, 0.05 - z * 0.9, y * 0.95 + 0.1)
    return [tuple(deitar(p) for p in tri[:3]) + tri[3:] for tri in malha_fantoche()]
