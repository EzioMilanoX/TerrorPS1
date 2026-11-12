# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""A terceira noite: a aldeia vazia.

Ruas de terra entre casas fechadas, lanternas de papel ainda acesas, a praca do poco, a
venda do velho, a escola, a torre de vigia, o banho publico, o cemiterio -- e a casa da
familia Mori, onde Ayame morava. Ninguem. So bonecas nas varandas (que se viram) e a
Imitadora: igual a Ayame, mas a de verdade foge de voce, e a falsa espera.

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

# as ruas
TRILHAS: list[list[P]] = [
    [INICIO, SANTUARIO], [(-30.0, 8.0), (30.0, 8.0)], [(-30.0, -12.0), (30.0, -12.0)],
    [(-18.0, 8.0), (-18.0, -12.0)], [(18.0, 8.0), (18.0, -12.0)],
    [(-26.0, 8.0), (-26.0, 26.0)], [(26.0, 8.0), (26.0, 26.0)], [(-26.0, 24.0), (26.0, 24.0)],
    [(-18.0, -12.0), (-22.0, -21.0)], [(18.0, -12.0), (22.0, -21.0)],
]
MARCOS: dict[str, P] = {
    "praca": (4.0, -2.0), "venda": (-9.0, 16.0), "escola": (12.0, 16.0), "torre": (-24.0, -1.0),
    "casa_mori": (11.0, -3.0), "cemiterio": (26.0, -26.0), "banho": (-24.0, -26.0),
}
NOME_MARCO = {"praca": "o poco da praca", "venda": "a venda do velho", "escola": "a escola",
              "torre": "a torre de vigia", "casa_mori": "a casa dos Mori", "cemiterio": "o cemiterio",
              "banho": "o banho publico"}
AMULETO_NO_MARCO = {"praca": (0.0, 1.3, 1.0), "venda": (0.6, 0.0, 1.0), "escola": (-0.5, 0.0, 0.85),
                    "torre": (1.6, 0.0, 0.5), "casa_mori": (-0.8, 0.0, 0.8), "cemiterio": (0.0, 0.0, 0.7),
                    "banho": (3.4, 0.0, 0.6)}
# casas: (x, z, largura em x, fundo em z, lado da porta: "n", "s", "l", "o")
CASAS: list[tuple[float, float, float, float, str]] = [
    (-9.0, 16.0, 6.0, 5.0, "l"), (12.0, 16.0, 9.0, 6.0, "o"), (11.0, -3.0, 6.0, 5.0, "o"),
    (-8.0, 1.0, 5.0, 4.0, "l"), (-9.0, -6.5, 5.0, 4.0, "l"), (-8.0, 29.0, 5.0, 4.0, "l"), (8.0, 29.0, 5.0, 4.0, "o"),
    (-17.0, 16.0, 4.0, 5.0, "n"), (19.0, 16.5, 4.0, 4.0, "n"), (-31.0, 16.0, 4.0, 5.0, "l"), (31.0, 16.0, 4.0, 5.0, "o"),
    (-31.0, -1.0, 4.0, 5.0, "l"), (31.0, -1.0, 4.0, 5.0, "o"), (-9.0, -19.0, 5.0, 4.0, "l"), (9.0, -19.0, 5.0, 4.0, "o"),
]
ESCONDERIJOS = {
    "no armario da venda": (-10.8, 17.6, 1.2, "seco"),
    "embaixo da varanda dos Mori": (7.4, -3.0, 0.3, "seco"),
    "no barril de agua do banho": (-20.2, -24.0, 0.75, "seco"),
}
HISTORIA = "Terceira noite. A aldeia vazia. Ayame anda por aqui -- ou alguem igual a ela."
TEXTOS = {
    "venda": "Fechei a venda. Todo mundo foi embora depois da enchente. Quem ficou ouve a menina chorando a noite.",
    "casa_mori": "Ayame desenhou a familia na parede: pai, mae, a irma, ela. E uma quinta pessoa, de branco, sem rosto.",
    "praca": "A de verdade nunca fica parada. Se ela esta parada te olhando, nao chegue perto. E nao vire as costas.",
    "escola": "Lista de chamada: dezessete alunos. Riscados, um por um, com a mesma letra.",
    "torre": "Da torre se ve a aldeia inteira. Vi duas meninas iguais, uma em cada ponta da rua.",
    "banho": "Se ela vier, entre no barril e nao saia. Ela esquece de quem some.",
    "cemiterio": "As lapides novas nao tem nome. So a data. Todas da mesma noite.",
}
BILHETE_INICIO = "ALDEIA -- EVACUADA. NAO RESPONDA A NINGUEM QUE CHAME PELO SEU NOME."


def dist_rua(x: float, z: float) -> float:
    return min(dist_segmento((x, z), t[i], t[i + 1]) for t in TRILHAS for i in range(len(t) - 1))


def _porta(x, z, w, d, lado) -> tuple[float, float]:
    """O ponto bem na frente da porta de uma casa."""
    return {"n": (x, z - d / 2 - 0.6), "s": (x, z + d / 2 + 0.6), "l": (x + w / 2 + 0.6, z),
            "o": (x - w / 2 - 0.6, z)}[lado]


def _paredes(x, z, w, d, lado) -> list[tuple[float, float, float, float]]:
    """As 4 paredes (caixas de colisao), com o vao da porta (1,4 m) no lado dela."""
    e, t = 0.1, 0.7  # espessura e meia porta
    x0, x1, z0, z1 = x - w / 2, x + w / 2, z - d / 2, z + d / 2
    caixas = []
    for nome, cx0, cz0, cx1, cz1, horizontal in (("n", x0, z0 - e, x1, z0 + e, True), ("s", x0, z1 - e, x1, z1 + e, True),
                                                 ("o", x0 - e, z0, x0 + e, z1, False), ("l", x1 - e, z0, x1 + e, z1, False)):
        if nome != lado:
            caixas.append((cx0, cz0, cx1, cz1))
        elif horizontal:
            caixas += [(cx0, cz0, x - t, cz1), (x + t, cz0, cx1, cz1)]
        else:
            caixas += [(cx0, cz0, cx1, z - t), (cx0, z + t, cx1, cz1)]
    return caixas


def gerar_mapa(semente: int = 13) -> Mapa:
    rng = random.Random(semente)
    m = Mapa(bioma="aldeia", nome="a aldeia vazia", historia=HISTORIA, inicio=INICIO, santuario=SANTUARIO,
             limite=LIMITE, marcos=dict(MARCOS), nome_marco=dict(NOME_MARCO), trilhas=TRILHAS,
             esconderijos=dict(ESCONDERIJOS), altar_oitavo=ALTAR_OITAVO, amuleto_no_marco=dict(AMULETO_NO_MARCO),
             tem_vulto=False, tem_pequena=False, tem_imitadora=True, estatua="boneca",
             nevoa=(30 / 255, 30 / 255, 38 / 255), neblina_longe=22.0)
    for nome, (mx, mz) in MARCOS.items():
        dx, dz, y = AMULETO_NO_MARCO[nome]
        m.amuletos.append((mx + dx, mz + dz, y))
    for x, z, w, d, lado in CASAS:
        m.caixas += _paredes(x, z, w, d, lado)
    _colisao(m)
    ocupado: list[P] = []
    for _ in range(5000):  # a mata em volta
        x, z = rng.uniform(-TAMANHO - 4, TAMANHO + 4), rng.uniform(-TAMANHO - 4, TAMANHO + 4)
        if abs(x) < LIMITE + 1 and abs(z) < LIMITE + 1:
            continue
        if any(abs(x - a) < 1.3 and abs(z - b) < 1.3 for a, b in ocupado[-60:]):
            continue
        ocupado.append((x, z))
        m.arvores.append((x, z, rng.uniform(8.0, 13.0), rng.random() < 0.1))
    portas = [_porta(*c) for c in CASAS]
    for px, pz in rng.sample(portas, 10):  # bonecas kokeshi nas varandas (elas se viram)
        m.espantalhos.append((px + rng.uniform(-0.6, 0.6), pz + rng.uniform(-0.3, 0.3)))
    while len(m.armadilhas) < 6:  # poucas: quem armou isso aqui?
        t = rng.choice(TRILHAS)
        k = rng.random()
        x, z = t[0][0] + (t[1][0] - t[0][0]) * k, t[0][1] + (t[1][1] - t[0][1]) * k
        longe = [INICIO, SANTUARIO, *MARCOS.values(), *portas] + m.armadilhas
        if all(math.hypot(x - p[0], z - p[1]) > 4.0 for p in longe):
            m.armadilhas.append((x, z))
    m.pilhas = [(1.2, 18.0), (-26.8, 14.0), (26.8, 20.0), (-1.2, -18.0), (17.0, 9.2)]
    m.bilhetes = [(INICIO[0] + 1.5, INICIO[1] - 0.6, 0.0, BILHETE_INICIO)]
    lugar = {"venda": (-8.0, 14.4, 0.0), "casa_mori": (12.0, -1.6, 0.0), "praca": (2.0, -0.8, 0.0),
             "escola": (10.0, 14.0, 0.0), "torre": (-22.0, 0.6, 0.0), "banho": (-20.6, -22.4, 0.0),
             "cemiterio": (23.6, -23.4, 0.0)}
    m.bilhetes += [(*lugar[k], t) for k, t in TEXTOS.items()]
    m.luzes = [((-8.5, 1.8, 16.0), (1.2, 0.65, 0.3), 5.0),  # a venda
               ((11.0, 1.6, -3.0), (1.1, 0.6, 0.3), 4.0),  # a casa dos Mori
               ((12.0, 2.0, 16.0), (0.5, 0.6, 0.9), 5.0),  # a escola, fria
               ((1.0, 2.2, 20.0), (1.4, 0.3, 0.2), 4.0), ((-1.0, 2.2, 6.0), (1.4, 0.3, 0.2), 4.0),  # lanternas de papel
               ((1.0, 2.2, -8.0), (1.4, 0.3, 0.2), 4.0), ((-1.0, 2.2, -20.0), (1.4, 0.3, 0.2), 4.0),
               ((-24.0, 4.5, -1.0), (1.0, 0.5, 0.25), 3.0),  # o lampiao no alto da torre
               ((-1.0, 1.0, -31.6), (1.5, 0.3, 0.15), 3.0)]  # a vela do santuario
    m.montar_grade()
    return m


def _colisao(m: Mapa) -> None:
    px, pz = MARCOS["praca"]
    m.circulos.append((px, pz, 1.0))  # o poco
    tx, tz = MARCOS["torre"]
    m.circulos += [(tx + dx, tz + dz, 0.25) for dx in (-1.2, 1.2) for dz in (-1.2, 1.2)]  # as pernas da torre
    bx, bz = MARCOS["banho"]
    m.caixas.append((bx - 3.0, bz - 2.5, bx + 3.0, bz + 2.5))  # o banho (fechado)
    m.circulos.append((bx + 3.8, bz + 2.0, 0.55))  # o barril
    cx, cz = MARCOS["cemiterio"]
    m.circulos += [(cx + i * 2.0, cz + j * 2.0, 0.3) for i in (-2, -1, 0, 1, 2) for j in (-1, 0, 1) if (i, j) != (0, 0)]
    sx, sz = SANTUARIO
    m.caixas.append((sx - 1.0, sz - 4.0, sx + 1.0, sz - 2.6))
    m.circulos += [(sx - 1.3, sz + 1.5, 0.3), (sx + 1.3, sz + 1.5, 0.3)]


# ------------------------------------------------------------------ geometria

PAREDE, TELHADO, SHOJI = (112, 98, 80), (44, 40, 44), (210, 200, 170)


def _casa(x, z, w, d, lado, aberta=False) -> list[Tri]:
    t: list[Tri] = []
    for x0, z0, x1, z1 in _paredes(x, z, w, d, lado):
        t += bloco(((x0 + x1) / 2, 0, (z0 + z1) / 2), 2.4, x1 - x0, x1 - x0, z1 - z0, PAREDE)
    t += bloco((x, 2.4, z), 3.8, w + 1.0, 0.3, d + 1.0, TELHADO)  # o telhado
    if not aberta:  # a porta de correr fechada, de papel
        if lado in ("n", "s"):
            t += bloco((x, 0, z + (d / 2 if lado == "s" else -d / 2)), 2.0, 1.4, 1.4, 0.05, SHOJI)
        else:
            t += bloco((x + (w / 2 if lado == "l" else -w / 2), 0, z), 2.0, 0.05, 0.05, 1.4, SHOJI)
    return t


def _venda(x, z) -> list[Tri]:
    t = bloco((x + 0.6, 0, z), 0.95, 0.8, 0.8, 2.6, MADEIRA)  # o balcao
    for k in range(3):
        t += bloco((x - 2.2, 0.5 + k * 0.6, z), 0.55 + k * 0.6, 0.5, 0.5, 3.0, MADEIRA_ESCURA)  # prateleiras
    t += bloco((x - 1.8, 0, z + 1.6), 2.0, 0.9, 0.9, 0.6, MADEIRA_ESCURA)  # o armario
    return t + bloco((x + 0.5, 0.95, z - 0.8), 1.25, 0.1, 0.08, 0.1, (230, 170, 90), emissivo=True)


def _escola(x, z) -> list[Tri]:
    t: list[Tri] = []
    for i in range(3):
        for j in range(2):  # carteiras
            t += bloco((x - 1.5 + i * 1.5, 0, z - 1.0 + j * 2.0), 0.7, 0.7, 0.7, 0.5, MADEIRA)
    return t + bloco((x + 3.6, 0.8, z), 2.0, 0.05, 0.05, 3.0, (30, 44, 36))  # a lousa


def _casa_mori(x, z) -> list[Tri]:
    t = bloco((x - 3.4, 0, z), 0.35, 0.8, 0.8, 5.0, MADEIRA)  # a varanda (engawa)
    t += bloco((x + 1.0, 0, z), 0.35, 1.2, 1.2, 0.8, MADEIRA_ESCURA)  # a mesa baixa
    t += bloco((x + 2.9, 0.9, z), 1.8, 0.04, 0.04, 2.4, (200, 190, 160))  # o desenho na parede
    for k, cor in enumerate(((60, 50, 60), (150, 40, 40), (60, 60, 80), (200, 200, 200), (250, 250, 250))):
        t += bloco((x + 2.85, 1.0, z - 0.9 + k * 0.45), 1.5, 0.02, 0.02, 0.15, cor)  # as cinco pessoas
    return t


def _praca(x, z) -> list[Tri]:
    t: list[Tri] = []
    for k in range(10):  # o poco
        a = k * 2 * math.pi / 10
        t += bloco((x + 0.85 * math.cos(a), 0, z + 0.85 * math.sin(a)), 0.9, 0.5, 0.45, 0.5, PEDRA)
    t += bloco((x, -0.5, z), 0.05, 1.2, 1.2, 1.2, (8, 8, 10))
    t += bloco((x, 2.0, z), 2.4, 2.4, 0.2, 1.4, TELHADO)
    for dx in (-0.95, 0.95):
        t += bloco((x + dx, 0, z), 2.0, 0.12, 0.1, 0.12, MADEIRA)
    t += bloco((x + 3.0, 0, z + 2.0), 4.0, 0.4, 0.15, 0.4, (58, 50, 44))  # uma arvore seca na praca
    return t


def _torre(x, z) -> list[Tri]:
    t: list[Tri] = []
    for dx in (-1.2, 1.2):
        for dz in (-1.2, 1.2):
            t += bloco((x + dx, 0, z + dz), 5.0, 0.18, 0.14, 0.18, MADEIRA_ESCURA)
    t += bloco((x, 4.2, z), 4.4, 3.0, 3.0, 3.0, MADEIRA)  # a plataforma
    t += bloco((x, 4.4, z), 6.0, 0.08, 0.08, 0.08, MADEIRA_ESCURA)
    t += icosaedro((x, 5.6, z), 0.35, (110, 90, 50))  # o sino
    t += cone((x, 6.0, z), 2.0, 1.2, TELHADO, lados=4)
    for k in range(8):  # a escada
        t += bloco((x + 1.6, k * 0.55, z), k * 0.55 + 0.06, 0.06, 0.06, 0.6, MADEIRA)
    return t


def _banho(x, z) -> list[Tri]:
    t = bloco((x, 0, z), 3.0, 6.0, 6.0, 5.0, (96, 90, 84))
    t += bloco((x, 3.0, z), 4.0, 6.8, 0.4, 5.8, TELHADO)
    t += bloco((x - 2.0, 3.0, z - 1.5), 7.5, 0.6, 0.45, 0.6, (80, 70, 64))  # a chamine
    t += bloco((x + 3.8, 0, z + 2.0), 1.0, 1.0, 1.0, 1.0, MADEIRA_ESCURA)  # o barril
    return t


def _cemiterio(x, z) -> list[Tri]:
    t: list[Tri] = []
    for i in (-2, -1, 0, 1, 2):
        for j in (-1, 0, 1):
            if (i, j) != (0, 0):
                alto = 0.8 + 0.3 * ((i * 7 + j * 3) % 3)
                t += bloco((x + i * 2.0, 0, z + j * 2.0), alto, 0.35, 0.3, 0.2, PEDRA)
    return t + bloco((x, 0, z), 0.5, 0.6, 0.5, 0.4, (90, 88, 84))  # a lapide do amuleto, sem nome


def _santuario() -> list[Tri]:
    sx, sz = SANTUARIO
    t = torii(sx, sz + 1.5, (100, 30, 26), (64, 20, 18))
    t += lanterna(sx - 1.6, sz + 0.2, (110, 108, 104), (255, 70, 40))
    t += bloco((sx, 0, sz - 3.3), 1.4, 1.8, 1.8, 1.3, MADEIRA_ESCURA)
    t += bloco((sx, 1.4, sz - 3.3), 2.0, 2.4, 0.2, 1.9, (40, 30, 28))
    return t


def geometria(m: Mapa) -> list[Tri]:
    rng = random.Random(3)

    def cor(x, z):
        tom = rng.uniform(-5, 5)
        if dist_rua(x, z) < 1.6:
            return (int(72 + tom), int(64 + tom), int(54 + tom))  # rua de terra
        if rng.random() < 0.25:
            return (int(44 + tom), int(52 + tom), int(38 + tom))  # mato no quintal
        return (int(56 + tom), int(52 + tom), int(46 + tom))

    tris = chao(-TAMANHO - 4, TAMANHO + 4, -TAMANHO - 4, TAMANHO + 4, 0.8, cor)
    for x, z, alto, seca in m.arvores:
        tris += _pinheiro(x, z, alto, (30, 40, 36)) if not seca else bloco((x, 0, z), alto * 0.7, 0.3, 0.08, 0.3, (58, 50, 44))
    abertas = {MARCOS["venda"], MARCOS["escola"], MARCOS["casa_mori"]}
    for x, z, w, d, lado in CASAS:
        tris += _casa(x, z, w, d, lado, aberta=(x, z) in abertas)
    for nome, f in (("venda", _venda), ("escola", _escola), ("casa_mori", _casa_mori), ("praca", _praca),
                    ("torre", _torre), ("banho", _banho), ("cemiterio", _cemiterio)):
        tris += f(*MARCOS[nome])
    for k in range(9):  # postes com lanternas de papel vermelhas ao longo da rua principal
        z = 27.0 - k * 6.0
        x = 1.0 if k % 2 == 0 else -1.0
        tris += bloco((x * 1.8, 0, z), 2.2, 0.1, 0.08, 0.1, MADEIRA_ESCURA)
        tris += icosaedro((x * 1.8, 2.3, z), 0.2, (220, 60, 40), emissivo=k % 3 != 2)  # algumas apagadas
    for k in range(14):  # cercas baixas
        x = -30.0 + k * 4.4
        if abs(x) > 3:
            tris += bloco((x, 0, 10.0), 0.8, 3.6, 3.6, 0.08, MADEIRA_ESCURA)
    tris += _santuario()
    tris += bloco((INICIO[0] + 1.5, 0, INICIO[1] - 1.0), 1.3, 0.1, 0.1, 0.1, MADEIRA)
    tris += bloco((INICIO[0] + 1.5, 1.0, INICIO[1] - 1.0), 1.35, 0.8, 0.8, 0.05, MADEIRA)
    for x, z, _, _ in m.bilhetes:
        tris += bloco((x, 0.02, z), 0.032, 0.22, 0.22, 0.3, (196, 188, 168))
    return tris


def malha_boneca() -> list[Tri]:
    """Uma kokeshi: corpo de madeira pintado, cabeca redonda, rosto de dois tracos. Olha para +z."""
    t = bloco((0, 0, 0), 0.38, 0.16, 0.12, 0.16, (170, 60, 50))
    t += bloco((0, 0.12, 0), 0.22, 0.165, 0.165, 0.165, (210, 180, 120))  # a faixa pintada
    t += icosaedro((0, 0.47, 0), 0.1, (220, 205, 180))
    t += bloco((0, 0.5, -0.02), 0.58, 0.2, 0.2, 0.16, (20, 16, 16))  # o cabelo
    for dx in (-0.035, 0.035):
        t += bloco((dx, 0.47, 0.09), 0.48, 0.03, 0.03, 0.02, (20, 16, 16))
    return t
