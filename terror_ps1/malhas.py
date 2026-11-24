# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""As malhas do jogo. Os construtores low poly vem da engine (`ouroboros.interfaces.malhas3d`:
`bloco`, `cone`, `esfera`, `plano`, `terreno`, `Malha` com `girada`/`transformada`/`juntar`);
aqui ficam so os modelos compostos do jogo (torii, lanterna de pedra, pinheiro, o vulto) e dois
ajustes que a engine nao tem: `deformada` (mexer vertice a vertice, sem desvirar triangulo) e
`movida` (transladar).

Para o visual ficar o mesmo de antes da troca: o `cone` do jogo e sempre sem tampa embaixo
(`tampa=False`, de baixo se ve o oco) e a `esfera` com `subdivisoes=0` e o icosaedro antigo.
Cena grande se monta numa lista de partes e um `juntar(*partes)` no fim (somar malha a malha
copia tudo a cada soma)."""
from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np
from ouroboros.interfaces.malhas3d import Malha, bloco, cone, esfera, juntar

__all__ = ["Malha", "altura_terra", "deformada", "escalada", "lanterna", "movida", "pinheiro", "torii", "vulto"]


def deformada(m: Malha, f: Callable[[np.ndarray], np.ndarray]) -> Malha:
    """A malha com cada vertice levado por `f` (recebe e devolve posicoes (V, 3)). Nao desvira
    triangulo nenhum: e o que os modelos antigos faziam (achatar uma esfera contra o chao)."""
    return Malha(f(m.posicoes.astype(np.float64)), m.cores, m.emissivo)


def movida(m: Malha, dx: float, dy: float, dz: float) -> Malha:
    return Malha(m.posicoes + np.array([dx, dy, dz], dtype=np.float32), m.cores, m.emissivo)


def escalada(m: Malha, ex: float, ey: float, ez: float, centro=(0.0, 0.0, 0.0)) -> Malha:
    """Esticada/achatada em cada eixo a partir de `centro`."""
    c = np.asarray(centro, dtype=np.float64)
    e = np.array([ex, ey, ez])
    return deformada(m, lambda p: (p - c) * e + c)


def altura_terra(x: float, z: float) -> float:
    """O chao irregular da floresta (o `Relevo` dela, e onde as coisas pequenas pousam)."""
    return 0.12 * math.sin(x * 1.3) * math.cos(z * 1.1) + 0.05 * math.sin(x * 3.1 + z * 2.3)


# ------------------------------------------------------------------ os modelos do jogo

def torii(x, z, vermelho, escuro, inclina=0.0) -> Malha:
    partes = [bloco((x + dx, 0, z), 3.0, 0.42, 0.34, 0.34, vermelho) for dx in (-1.3, 1.3)]  # os pilares
    partes += [bloco((x, 3.0, z), 3.3, 4.2, 4.6, 0.5, vermelho),  # a viga de cima e a de baixo
               bloco((x, 3.3, z), 3.42, 4.7, 4.9, 0.56, escuro),
               bloco((x, 2.35, z), 2.55, 3.2, 3.2, 0.3, escuro)]
    m = juntar(*partes)
    return m.girada("z", inclina, (x, 0, z)) if inclina else m


def lanterna(x, z, pedra, luz, acesa=True, quebrada=False) -> Malha:
    """Um toro de pedra: base, haste, plataforma, a caixa da chama, o telhado e a ponta."""
    escura = tuple(int(c * 0.75) for c in pedra)
    m = bloco((x, 0, z), 0.15, 0.5, 0.45, 0.5, pedra) + bloco((x, 0.15, z), 0.75, 0.18, 0.15, 0.18, pedra)
    if quebrada:
        return m + bloco((x + 0.5, 0, z + 0.3), 0.2, 0.62, 0.55, 0.5, escura)  # o telhado caido
    return juntar(m, bloco((x, 0.75, z), 0.85, 0.42, 0.42, 0.42, pedra),
                  bloco((x, 0.85, z), 1.13, 0.28, 0.28, 0.28, luz if acesa else escura, emissivo=acesa),
                  bloco((x, 1.13, z), 1.33, 0.64, 0.1, 0.64, escura),
                  esfera((x, 1.38, z), 0.06, escura, subdivisoes=0))


def pinheiro(x, z, alto, cor) -> Malha:
    partes = [bloco((x, 0, z), alto * 0.3, 0.2, 0.14, 0.2, (64, 46, 40))]
    for k in range(3):
        tom = tuple(min(255, int(c * (0.85 + 0.12 * k))) for c in cor)
        partes.append(cone((x, alto * (0.2 + 0.22 * k), z), alto * 0.27 * (1 - 0.24 * k), alto * 0.42, tom,
                           lados=7, tampa=False))
    return juntar(*partes)


def vulto(x: float, z: float) -> Malha:
    """Alto demais, magro demais, bracos ate abaixo dos joelhos, dedos compridos e a cabeca
    alongada e torta, com olhos e boca escuros. Olha para +z (o jogo gira para o jogador)."""
    pele, escuro = (150, 144, 132), (16, 10, 10)
    partes = [bloco((x + dx, 0, z), 1.05, 0.07, 0.09, 0.08, pele) for dx in (-0.09, 0.09)]  # pernas finas
    partes.append(bloco((x, 1.0, z), 1.95, 0.2, 0.38, 0.16, pele))  # tronco: estreito embaixo, ombro largo
    for dx in (-0.22, 0.22):  # bracos compridos demais
        partes.append(bloco((x + dx, 0.55, z), 1.92, 0.05, 0.08, 0.06, pele))
        for k in (-1, 0, 1):
            partes.append(bloco((x + dx + k * 0.022, 0.36, z + 0.01), 0.56, 0.012, 0.014, 0.012, pele))
    partes.append(bloco((x, 1.93, z), 2.22, 0.06, 0.055, 0.06, pele))  # pescoco comprido
    cy = 2.38
    cabeca = [escalada(esfera((x, cy, z), 0.14, pele, subdivisoes=1), 1.0, 1.45, 1.0, (0.0, cy, 0.0))]
    for dx in (-0.05, 0.05):  # os olhos
        cabeca.append(bloco((x + dx, cy + 0.03, z + 0.13), cy + 0.08, 0.045, 0.04, 0.04, escuro))
    cabeca.append(bloco((x, cy - 0.15, z + 0.12), cy - 0.04, 0.025, 0.035, 0.04, escuro))  # a boca, aberta
    partes.append(juntar(*cabeca).girada("z", 0.38, (x, 2.22, z)))  # a cabeca tomba de lado
    return juntar(*partes)
