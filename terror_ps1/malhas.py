# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""As malhas do jogo: os construtores low poly (bloco, cone, icosaedro, chao, torii,
lanterna de pedra) e o vulto. Vieram da vitrine de estilos da OuroborosEngine
(`games/vitrine_estilos/tres_d.py`); aqui so a geometria, sem o rasterizador de CPU."""
from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence

import numpy as np

Vec = tuple[float, float, float]
Cor = tuple[int, int, int]
Tri = tuple[Vec, Vec, Vec, Cor, bool, int]  # tres vertices, a cor, se emite luz, a camada
FUNDO, CHAO, OBJETO = 0, 1, 2


def _unit(v) -> np.ndarray:
    v = np.asarray(v, dtype=np.float64)
    return v / np.linalg.norm(v)


# ------------------------------------------------------------------ malhas

def _rot_z(p: Vec, pivo: Vec, ang: float) -> Vec:
    c, s = math.cos(ang), math.sin(ang)
    x, y = p[0] - pivo[0], p[1] - pivo[1]
    return (pivo[0] + x * c - y * s, pivo[1] + x * s + y * c, p[2])


def _normal(a: Vec, b: Vec, c: Vec) -> Vec:
    u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    return (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])


def _fechada(v: Sequence[Vec], faces, cor, emissivo=False, camada=OBJETO, centro=None) -> list[Tri]:
    """Os triangulos de uma malha fechada, cada um virado para FORA (a normal longe do
    centro): e o que o backface culling e a luz esperam."""
    c = centro or tuple(sum(p[i] for p in v) / len(v) for i in range(3))
    out: list[Tri] = []
    for i, j, k in faces:
        a, b, d = v[i], v[j], v[k]
        n = _normal(a, b, d)
        m = [(a[x] + b[x] + d[x]) / 3 - c[x] for x in range(3)]
        if n[0] * m[0] + n[1] * m[1] + n[2] * m[2] < 0:
            b, d = d, b
        out.append((a, b, d, cor, emissivo, camada))
    return out


def _para_cima(a: Vec, b: Vec, c: Vec, cor: Cor, camada: int) -> Tri:
    return (a, b, c, cor, False, camada) if _normal(a, b, c)[1] >= 0 else (a, c, b, cor, False, camada)


_FACES_BLOCO = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
                (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]


def bloco(base, topo, larg_base, larg_topo, prof, cor, ang=0.0, pivo=None, emissivo=False) -> list[Tri]:
    """Tronco de piramide (caixa se as larguras forem iguais) da `base` ate a altura `topo`,
    girado `ang` em volta de `pivo`: 8 vertices, 12 triangulos."""
    bx, by, bz = base
    lb, lt, d = larg_base / 2, larg_topo / 2, prof / 2
    v = [(bx - lb, by, bz - d), (bx + lb, by, bz - d), (bx + lb, by, bz + d), (bx - lb, by, bz + d),
         (bx - lt, topo, bz - d), (bx + lt, topo, bz - d), (bx + lt, topo, bz + d), (bx - lt, topo, bz + d)]
    if ang:
        v = [_rot_z(p, pivo or base, ang) for p in v]
    return _fechada(v, _FACES_BLOCO, cor, emissivo)


def icosaedro(centro, raio, cor, emissivo=False, sub=0, camada=OBJETO) -> list[Tri]:
    t = (1 + 5 ** 0.5) / 2
    vs = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
          (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    fs = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
          (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10),
          (8, 6, 7), (9, 8, 1)]
    vs = [tuple(c / math.sqrt(sum(x * x for x in p)) for c in p) for p in vs]
    for _ in range(sub):  # cada triangulo vira 4, empurrados para a esfera
        novos, meio = [], {}

        def m(a, b):
            k = (min(a, b), max(a, b))
            if k not in meio:
                p = [(vs[a][i] + vs[b][i]) / 2 for i in range(3)]
                n = math.sqrt(sum(x * x for x in p))
                vs.append(tuple(x / n for x in p))
                meio[k] = len(vs) - 1
            return meio[k]

        for a, b, c in fs:
            ab, bc, ca = m(a, b), m(b, c), m(c, a)
            novos += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        fs = novos
    p = [(centro[0] + x * raio, centro[1] + y * raio, centro[2] + z * raio) for x, y, z in vs]
    return _fechada(p, fs, cor, emissivo, camada, centro)


def cone(base, raio, altura, cor, lados=7) -> list[Tri]:
    bx, by, bz = base
    pts = [(bx + raio * math.cos(2 * math.pi * i / lados), by, bz + raio * math.sin(2 * math.pi * i / lados))
           for i in range(lados)]
    v = pts + [(bx, by + altura, bz)]
    return _fechada(v, [(i, (i + 1) % lados, lados) for i in range(lados)], cor, centro=(bx, by + altura / 3, bz))


def chao(x0, x1, z0, z1, passo, cor: Callable[[float, float], Cor],
         altura: Callable[[float, float], float] = lambda x, z: 0.0, camada=CHAO, passo_z=None) -> list[Tri]:
    """Uma grade de ladrilhos: triangulo grande demais some perto da camera, e a luz por
    vertice precisa de vertices para variar."""
    tris: list[Tri] = []

    def p(x, z):
        return (x, altura(x, z), z)

    pz = passo_z or passo
    for j in range(round((z1 - z0) / pz)):
        for i in range(round((x1 - x0) / passo)):
            xa, za = x0 + i * passo, z0 + j * pz
            a, b, c, d = p(xa, za), p(xa + passo, za), p(xa + passo, za + pz), p(xa, za + pz)
            k = cor(xa + passo / 2, za + pz / 2)
            tris += [_para_cima(a, b, c, k, camada), _para_cima(a, c, d, k, camada)]
    return tris


def montanhas(z0, z1, x0, x1, n, alto, seed, cor) -> list[Tri]:
    rng = random.Random(seed)
    alt = [[max(0.0, rng.uniform(0.2, 1.0) * alto * math.sin(math.pi * j / n)) for _ in range(n + 1)]
           for j in range(n + 1)]
    return chao(x0, x1, z0, z1, (x1 - x0) / n, lambda x, z: cor,
                lambda x, z: alt[round((z - z0) / (z1 - z0) * n)][round((x - x0) / (x1 - x0) * n)], FUNDO,
                (z1 - z0) / n)


# ------------------------------------------------------------------ a cena

def torii(x, z, vermelho, escuro, inclina=0.0) -> list[Tri]:
    tris: list[Tri] = []
    for dx in (-1.3, 1.3):  # dois pilares, a viga de cima e a de baixo
        tris += bloco((x + dx, 0, z), 3.0, 0.42, 0.34, 0.34, vermelho)
    tris += bloco((x, 3.0, z), 3.3, 4.2, 4.6, 0.5, vermelho)
    tris += bloco((x, 3.3, z), 3.42, 4.7, 4.9, 0.56, escuro)
    tris += bloco((x, 2.35, z), 2.55, 3.2, 3.2, 0.3, escuro)
    if inclina:
        tris = [tuple(_rot_z(p, (x, 0, z), inclina) for p in t[:3]) + t[3:] for t in tris]
    return tris


def lanterna(x, z, pedra, luz, acesa=True, quebrada=False) -> list[Tri]:
    """Um toro de pedra: base, haste, plataforma, a caixa da chama, o telhado e a ponta."""
    escura = tuple(int(c * 0.75) for c in pedra)
    tris = bloco((x, 0, z), 0.15, 0.5, 0.45, 0.5, pedra) + bloco((x, 0.15, z), 0.75, 0.18, 0.15, 0.18, pedra)
    if quebrada:
        return tris + bloco((x + 0.5, 0, z + 0.3), 0.2, 0.62, 0.55, 0.5, escura)  # o telhado caido
    tris += bloco((x, 0.75, z), 0.85, 0.42, 0.42, 0.42, pedra)
    tris += bloco((x, 0.85, z), 1.13, 0.28, 0.28, 0.28, luz if acesa else escura, emissivo=acesa)
    tris += bloco((x, 1.13, z), 1.33, 0.64, 0.1, 0.64, escura)
    return tris + icosaedro((x, 1.38, z), 0.06, escura)


def pinheiro(x, z, alto, cor) -> list[Tri]:
    tris = bloco((x, 0, z), alto * 0.3, 0.2, 0.14, 0.2, (64, 46, 40))
    for k in range(3):
        tom = tuple(min(255, int(c * (0.85 + 0.12 * k))) for c in cor)
        tris += cone((x, alto * (0.2 + 0.22 * k), z), alto * 0.27 * (1 - 0.24 * k), alto * 0.42, tom)
    return tris




def _altura_terra(x: float, z: float) -> float:
    return 0.12 * math.sin(x * 1.3) * math.cos(z * 1.1) + 0.05 * math.sin(x * 3.1 + z * 2.3)


def vulto(x: float, z: float) -> list[Tri]:
    """Alto demais, magro demais, bracos ate abaixo dos joelhos, dedos compridos e a cabeca
    alongada e torta, com olhos e boca escuros. Olha para +z (o jogo gira para o jogador)."""
    pele, escuro = (150, 144, 132), (16, 10, 10)
    tris: list[Tri] = []
    for dx in (-0.09, 0.09):  # pernas finas
        tris += bloco((x + dx, 0, z), 1.05, 0.07, 0.09, 0.08, pele)
    tris += bloco((x, 1.0, z), 1.95, 0.2, 0.38, 0.16, pele)  # tronco: estreito embaixo, ombro largo
    for dx in (-0.22, 0.22):  # bracos compridos demais
        tris += bloco((x + dx, 0.55, z), 1.92, 0.05, 0.08, 0.06, pele)
        for k in (-1, 0, 1):
            tris += bloco((x + dx + k * 0.022, 0.36, z + 0.01), 0.56, 0.012, 0.014, 0.012, pele)
    tris += bloco((x, 1.93, z), 2.22, 0.06, 0.055, 0.06, pele)  # pescoco comprido
    cy = 2.38
    cabeca = icosaedro((x, cy, z), 0.14, pele, sub=1)
    cabeca = [tuple((p[0], cy + (p[1] - cy) * 1.45, p[2]) for p in t[:3]) + t[3:] for t in cabeca]
    for dx in (-0.05, 0.05):  # os olhos
        cabeca += bloco((x + dx, cy + 0.03, z + 0.13), cy + 0.08, 0.045, 0.04, 0.04, escuro)
    cabeca += bloco((x, cy - 0.15, z + 0.12), cy - 0.04, 0.025, 0.035, 0.04, escuro)  # a boca, aberta
    pivo = (x, 2.22, z)  # a cabeca tomba de lado
    return tris + [tuple(_rot_z(p, pivo, 0.38) for p in t[:3]) + t[3:] for t in cabeca]


