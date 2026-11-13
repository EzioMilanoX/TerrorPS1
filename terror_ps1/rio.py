# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""A noite secreta: Sai no Kawara, a margem do rio.

So abre para quem deixou o oitavo omamori no altar em todas as sete noites. A margem de pedras
onde as criancas empilham torres para atravessar o rio; de noite alguem derruba, e elas empilham
de novo. O Jizo grande, os cata-ventos. Nao ha monstro. A Ayame esta aqui, escondida atras de
uma das pedras grandes, cantarolando a musica da roda: a brincadeira ainda nao acabou
(`regras._esconde`). Ache ela no escuro e diga "achei voce" (ESPACO).

Mesmo contrato da floresta (`mapa.Mapa`): `gerar_mapa()` e `geometria()`.
"""
from __future__ import annotations

import math
import random

from terror_ps1.malhas import Tri, bloco, chao, icosaedro
from terror_ps1.mapa import MADEIRA, Mapa, P, _pinheiro, dist_segmento

TAMANHO = 40.0
LIMITE = 37.5
INICIO: P = (0.0, 32.0)
JIZO: P = (0.0, -11.0)  # o Jizo grande, de frente para o rio (o "santuario" desta noite)
RASO, FUNDO = -16.0, -19.5  # a agua: rasa a partir daqui, funda depois
TRILHA: list[P] = [INICIO, (2.0, 22.0), (-1.5, 10.0), (0.5, 0.0), (0.0, -8.0)]
# onde ela se esconde: atras de cada pedra grande (a pedra fica entre ela e quem vem do sul)
ESCONDE: list[P] = [(-14.0, 13.0), (14.0, 17.0), (-21.0, -6.0), (19.0, -9.0), (-6.0, -3.0), (9.0, 4.0)]
ROCHA = 1.1  # a pedra, ao sul dela
HISTORIA = "A margem do rio. Sai no Kawara. Ela ainda esta escondida."
TEXTOS = (
    ((2.6, 27.0), "Aqui as criancas empilham pedras para atravessar o rio. De noite, alguem derruba. "
                  "Elas empilham de novo."),
    ((-3.2, 16.0), "Ela ainda esta brincando. Ela ainda esta escondida, esperando alguem achar."),
    ((2.2, 5.0), "Se a luz achar ela de longe, nao vale: ela ri e se esconde de novo."),
    ((-2.0, -4.0), "No escuro, escute. Ela cantarola a musica da roda."),
    ((1.8, -9.4), "O Jizo guarda as criancas na manga. Nao guardou a que ninguem procurou."),
)
BILHETE_INICIO = "Achei voce. -- diga isso de perto."


def agua(x: float, z: float) -> int:
    return 2 if z < FUNDO else 1 if z < RASO else 0


def dist_trilha(x: float, z: float) -> float:
    return min(dist_segmento((x, z), TRILHA[i], TRILHA[i + 1]) for i in range(len(TRILHA) - 1))


def rochas() -> list[P]:
    return [(x, z + ROCHA) for x, z in ESCONDE]


def _livre(x: float, z: float) -> bool:
    if dist_trilha(x, z) < 1.6 or z < RASO + 0.5:
        return False
    if math.hypot(x - INICIO[0], z - INICIO[1]) < 4.0 or math.hypot(x - JIZO[0], z - JIZO[1]) < 4.0:
        return False
    return all(math.hypot(x - a, z - b) > 2.8 for a, b in ESCONDE + rochas())


def gerar_mapa(semente: int = 53) -> Mapa:
    rng = random.Random(semente)
    m = Mapa(bioma="rio", nome="a margem do rio", historia=HISTORIA, inicio=INICIO, santuario=JIZO,
             limite=LIMITE, marcos={"jizo": JIZO}, nome_marco={"jizo": "o Jizo"}, trilhas=[list(TRILHA)],
             esconderijos={}, altar_oitavo=JIZO, tem_vulto=False, agua=agua, tem_esconde=True,
             esconde_lugares=list(ESCONDE), nevoa=(64 / 255, 70 / 255, 86 / 255), neblina_longe=18.0)
    for _ in range(700):  # as torres de pedra das criancas
        x, z = rng.uniform(-LIMITE + 1, LIMITE - 1), rng.uniform(RASO + 0.5, LIMITE - 1)
        if not _livre(x, z) or any(math.hypot(x - a, z - b) < 1.4 for a, b, _ in m.pedras):
            continue
        m.pedras.append((x, z, rng.randrange(2, 7)))  # x, z, quantas pedras
        m.circulos.append((x, z, 0.28))
    for rx, rz in rochas():
        m.circulos.append((rx, rz, 1.0))
    m.circulos.append((JIZO[0], JIZO[1], 0.9))
    for _ in range(500):  # arvores mortas nas duas beiras: uma parede
        x, z = rng.choice((-1, 1)) * rng.uniform(31.0, TAMANHO + 4), rng.uniform(RASO, TAMANHO + 4)
        m.arvores.append((x, z, rng.uniform(6.0, 10.0), False))
        if abs(x) < LIMITE + 1:
            m.circulos.append((x, z, 0.35))
    m.pilhas = [(-2.6, 20.0), (3.0, -1.0)]
    m.bilhetes = [(INICIO[0] + 1.5, INICIO[1] - 0.6, 0.0, BILHETE_INICIO)]
    m.bilhetes += [(x, z, 0.0, t) for (x, z), t in TEXTOS]
    m.luzes = [((JIZO[0] - 0.8, 0.3, JIZO[1] + 0.9), (1.2, 0.7, 0.3), 3.0),  # as velas aos pes do Jizo
               ((0.0, 0.4, -24.0), (0.4, 0.5, 0.8), 9.0)]  # o rio, claro de lua
    m.montar_grade()
    return m


# ------------------------------------------------------------------ geometria

SEIXO, AGUA_RASA, AGUA_FUNDA = (96, 96, 98), (40, 52, 66), (18, 24, 36)


def _torre(x, z, n, rng) -> list[Tri]:
    t, y, larg = [], 0.0, 0.34
    for _ in range(int(n)):
        alto = rng.uniform(0.09, 0.14)
        tom = rng.randint(-14, 14)
        t += bloco((x + rng.uniform(-0.03, 0.03), y, z), y + alto, larg, larg * 0.9, larg * 0.9,
                   (110 + tom, 108 + tom, 104 + tom))
        y += alto
        larg *= 0.82
    return t


def _jizo() -> list[Tri]:
    x, z = JIZO
    t = bloco((x, 0, z), 0.5, 1.6, 1.6, 1.4, (80, 80, 82))  # a base
    t += bloco((x, 0.5, z), 2.4, 1.0, 0.8, 0.8, (120, 118, 112))  # o corpo
    t += icosaedro((x, 2.75, z), 0.42, (126, 124, 118))  # a cabeca
    t += bloco((x, 1.6, z + 0.42), 2.2, 0.9, 0.8, 0.06, (170, 40, 34))  # o babador
    for k in range(5):  # as velas
        t += bloco((x - 1.0 + k * 0.5, 0.0, z + 1.0), 0.25, 0.05, 0.05, 0.05, (220, 214, 190))
        t += bloco((x - 1.0 + k * 0.5, 0.25, z + 1.0), 0.29, 0.02, 0.02, 0.02, (255, 190, 90), emissivo=True)
    return t


def _cata_ventos(rng) -> list[Tri]:
    t = []
    for k in range(14):  # espetados na terra em volta do Jizo
        a = k / 14 * 2 * math.pi
        x, z = JIZO[0] + math.cos(a) * rng.uniform(2.0, 3.2), JIZO[1] + math.sin(a) * rng.uniform(2.0, 3.2)
        if z < RASO + 0.4:
            continue
        t += bloco((x, 0, z), 0.8, 0.02, 0.02, 0.02, MADEIRA)
        cor = rng.choice(((200, 50, 50), (220, 200, 80), (80, 140, 200), (220, 130, 170)))
        t += bloco((x, 0.7, z), 0.92, 0.22, 0.22, 0.02, cor, rng.uniform(0, 1.5), (x, 0.81, z))
    return t


def geometria(m: Mapa) -> list[Tri]:
    rng = random.Random(5)

    def cor(x, z):
        tom = rng.uniform(-8, 8)
        if z < FUNDO:
            return (int(AGUA_FUNDA[0] + tom / 3), int(AGUA_FUNDA[1] + tom / 3), int(AGUA_FUNDA[2] + tom / 2))
        if z < RASO:
            return (int(AGUA_RASA[0] + tom / 2), int(AGUA_RASA[1] + tom / 2), int(AGUA_RASA[2] + tom / 2))
        if dist_trilha(x, z) < 1.0:
            return (int(84 + tom), int(82 + tom), int(78 + tom))
        return (int(SEIXO[0] + tom), int(SEIXO[1] + tom), int(SEIXO[2] + tom))

    tris = chao(-TAMANHO - 4, TAMANHO + 4, -TAMANHO - 4, TAMANHO + 4, 1.0, cor)
    for x, z, alto, _ in m.arvores:
        tris += _pinheiro(x, z, alto, (40, 42, 44))
    rt = random.Random(7)
    for x, z, n in m.pedras:
        tris += _torre(x, z, n, rt)
    for rx, rz in rochas():  # as pedras grandes
        tris += icosaedro((rx, 0.55, rz), 1.0, (88, 90, 92))
    tris += _jizo() + _cata_ventos(random.Random(3))
    tris += bloco((INICIO[0] + 1.5, 0, INICIO[1] - 1.0), 1.3, 0.1, 0.1, 0.1, MADEIRA)
    tris += bloco((INICIO[0] + 1.5, 1.0, INICIO[1] - 1.0), 1.35, 0.8, 0.8, 0.05, MADEIRA)
    for x, z, _, _ in m.bilhetes:
        tris += bloco((x, 0.02, z), 0.032, 0.22, 0.22, 0.3, (196, 188, 168))
    return tris
