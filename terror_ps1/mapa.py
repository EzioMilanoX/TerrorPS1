# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""O mapa da floresta: 80x80, trilhas ligando sete marcos e o santuario do torii.

`gerar_mapa()` decide ONDE fica cada coisa (dados puros, deterministicos pela semente):
trilhas, arvores, pedras, marcos, os sete amuletos (um por marco), pilhas, armadilhas de
urso e gravetos (quase todos nas trilhas -- e por onde se anda), placas e bilhetes.
`geometria()` transforma o que nunca muda numa `Malha` (construtores da engine,
`ouroboros.interfaces.malhas3d`) para o `IRenderer3D`. O que a floresta muda quando voce nao
olha (jizos, a arvore morta, as placas) e os itens ficam fora: sao malhas centradas na
origem, desenhadas com matriz de modelo.

A colisao e a visao moram num `MundoColisao3D` da engine (`Mapa.mundo`, montado por
`Mapa.montar_colisao()` a partir de `circulos` e `caixas`): cada circulo vira uma capsula em
pe, cada caixa um AABB. O que e mais baixo que `VISAO_MIN` (pedra, mesa, poco, tumulo baixo)
segura o corpo mas nao tapa a visao.
"""
from __future__ import annotations

import dataclasses
import math
import random
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
from ouroboros.core.colisao3d import AABB, Capsula, MundoColisao3D, Relevo
from ouroboros.interfaces.malhas3d import Malha, bloco, cone, esfera, juntar, terreno

from terror_ps1.malhas import altura_terra, deformada, escalada, lanterna, movida, torii

P = tuple[float, float]
TAMANHO = 40.0  # o mapa vai de -40 a 40 em x e z
# a colisao: camadas do MundoColisao3D e as alturas dos obstaculos
CORPO, VISAO = 1, 2  # o que segura quem anda; o que tapa a visao
ALTO = 4.0  # altura de um obstaculo sem altura dada (tronco, parede): acima dos olhos de todos
VISAO_MIN = 1.2  # mais baixo que isso, o obstaculo nao tapa a visao
_CORPO_MIN = 2.0  # todo colisor vai pelo menos ate aqui: o corpo inteiro encosta de lado
ESPACO_ARVORES = 3.4  # distancia minima entre troncos na area jogavel
LIMITE = 37.5  # ate onde se anda (o resto e a parede de arvores)
INICIO: P = (0.0, 34.0)
SANTUARIO: P = (0.0, -30.0)
MARCOS: dict[str, P] = {
    "cabana": (-22.0, 2.0), "poco": (24.0, -6.0), "arvore_morta": (-18.0, -22.0), "pedras": (20.0, 22.0),
    "jizo": (8.0, -14.0), "troncos": (-8.0, 18.0), "acampamento": (-30.0, -8.0),
}
NOME_MARCO = {"cabana": "a cabana", "poco": "o poco", "arvore_morta": "a arvore morta", "pedras": "o circulo de pedras",
              "jizo": "os jizos", "troncos": "os troncos caidos", "acampamento": "o acampamento"}
ARVORE_MORTA_OUTRA: P = (14.0, -22.0)  # para onde a arvore das fitas vai quando ninguem olha
# placas nas bifurcacoes: (posicao, para qual marco apontam) -- e elas mentem
PLACAS: list[tuple[P, str]] = [((1.4, 5.4), "cabana"), ((13.4, 1.2), "poco"), ((3.4, 22.8), "pedras"),
                               ((-5.4, 12.8), "troncos"), ((1.6, -26.6), "arvore_morta"), ((-23.4, -1.6), "acampamento")]
# onde da para se esconder: (x, z, altura dos olhos la dentro)
_CAB, _POC, _ACA = (-22.0, 2.0), (24.0, -6.0), (-30.0, -8.0)
ESCONDERIJOS: dict[str, tuple[float, float, float]] = {
    "atras da mesa": (_CAB[0] + 0.4, _CAB[1] + 1.2, 0.5),  # entre a mesa e a parede, encolhido
    "dentro do poco": (_POC[0], _POC[1], 0.95),  # os olhos na altura da borda
    "na barraca caida": (_ACA[0] + 1.05, _ACA[1], 0.45),  # debaixo da lona, espiando para fora
}
ALTAR_OITAVO = (0.0, -32.3)  # onde o oitavo omamori aparece, na frente do santuario
# onde ficam as paginas do diario na floresta (na beira das trilhas)
LUGAR_PAGINAS: list[P] = [(1.6, 30.0), (-3.0, 16.5), (10.6, -2.4), (-15.0, 5.4), (17.6, 14.0), (-27.4, -4.2),
                          (5.6, -18.0), (-12.0, -24.0), (13.0, 26.6)]
RAIO_MARCO = {"cabana": 6.0, "poco": 4.0, "arvore_morta": 4.5, "pedras": 5.0, "jizo": 4.5, "troncos": 5.0,
              "acampamento": 5.0}
# onde o amuleto de cada marco fica (relativo ao marco) e a que altura
AMULETO_NO_MARCO = {"cabana": (0.4, 0.6, 0.95), "poco": (0.0, 1.05, 0.95), "arvore_morta": (0.0, 0.85, 0.5),
                    "pedras": (0.0, 0.0, 0.75), "jizo": (3.4, -1.0, 0.45), "troncos": (0.5, 0.0, 0.95),
                    "acampamento": (0.0, 1.9, 0.4)}
TRILHAS: list[list[P]] = [
    [INICIO, (2.0, 24.0), (-4.0, 14.0), (0.0, 4.0), (6.0, -6.0), (8.0, -12.0), (2.0, -24.0), (0.0, -28.0)],
    [(0.0, 4.0), (-12.0, 4.0), (-19.0, 2.0)],
    [(0.0, 4.0), (12.0, 0.0), (22.0, -5.0)],
    [(-22.0, 0.0), (-26.0, -5.0), (-29.0, -6.5)],
    [(0.0, -28.0), (-10.0, -26.0), (-17.0, -22.5)],
    [(2.0, 24.0), (10.0, 27.0), (18.0, 23.0)],
    [(-4.0, 14.0), (-7.0, 17.0)],
    [(12.0, 0.0), (16.0, 12.0), (19.0, 19.0)],
]


def dist_segmento(p: P, a: P, b: P) -> float:
    ax, az, bx, bz = a[0], a[1], b[0], b[1]
    dx, dz = bx - ax, bz - az
    t = 0.0 if dx == dz == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - az) * dz) / (dx * dx + dz * dz)))
    return math.hypot(p[0] - ax - t * dx, p[1] - az - t * dz)


def dist_trilha(p: P, trilhas: list[list[P]] | None = None) -> float:
    return min(dist_segmento(p, t[i], t[i + 1]) for t in (trilhas or TRILHAS) for i in range(len(t) - 1))


@dataclass
class Mapa:
    arvores: list[tuple[float, float, float, bool]] = field(default_factory=list)  # x, z, altura, seca
    pedras: list[tuple[float, float, float]] = field(default_factory=list)  # x, z, raio
    amuletos: list[tuple[float, float, float]] = field(default_factory=list)  # x, z, altura
    pilhas: list[P] = field(default_factory=list)
    armadilhas: list[P] = field(default_factory=list)
    # colisao: x, z, raio[, altura] e x0, z0, x1, z1[, altura] (sem altura: `ALTO`, tapa a visao)
    circulos: list[tuple[float, ...]] = field(default_factory=list)
    caixas: list[tuple[float, ...]] = field(default_factory=list)
    luzes: list[tuple[tuple[float, float, float], tuple[float, float, float], float]] = field(default_factory=list)
    jizos: list[P] = field(default_factory=list)  # as estatuas (giram para voce quando voce nao olha)
    paginas: list[P] = field(default_factory=list)  # as paginas do diario espalhadas
    gravetos: list[P] = field(default_factory=list)  # estalam se pisados de pe
    bilhetes: list[tuple[float, float, float, str]] = field(default_factory=list)  # x, z, altura, texto
    # o bioma: cada noite tem o seu mapa, e as regras leem daqui (nao de constantes do modulo)
    bioma: str = "floresta"
    nome: str = "a floresta"
    historia: str = ""
    inicio: P = (0.0, 34.0)
    santuario: P = (0.0, -30.0)
    limite: float = 37.5
    marcos: dict[str, P] = field(default_factory=dict)
    nome_marco: dict[str, str] = field(default_factory=dict)
    trilhas: list[list[P]] = field(default_factory=list)
    esconderijos: dict[str, tuple[float, float, float, str]] = field(default_factory=dict)  # x, z, olhos, "seco"/"agua"
    altar_oitavo: P = (0.0, -32.3)
    arvore_outra: P | None = None
    amuleto_no_marco: dict[str, tuple[float, float, float]] = field(default_factory=dict)
    placas: list[tuple[P, str]] = field(default_factory=list)
    espantalhos: list[P] = field(default_factory=list)  # giram para voce, como os jizos
    tem_vulto: bool = True
    tem_pequena: bool = False  # a floresta e so do vulto; a pequena e da escola (noite 6)
    pequena_aparece: int = 5  # com quantos omamori ela aparece
    tem_roda: bool = False  # a setima noite: a roda (Kagome)
    roda_centro: P | None = None  # chegou aqui, a roda fecha
    tem_esconde: bool = False  # a noite secreta: a Ayame escondida (esconde-esconde)
    esconde_lugares: list[P] = field(default_factory=list)  # onde ela pode estar
    fogo: bool = False  # o pesadelo: a noite pegando fogo (e dois monstros)
    fogos: list[P] = field(default_factory=list)  # onde queima
    tem_cego: bool = False
    tem_imitadora: bool = False
    tem_farejador: bool = False
    farejador_inicio: P | None = None
    tem_fantoche: bool = False
    fantoche_inicio: P | None = None
    tocos: list[P] = field(default_factory=list)  # tocos de bambu em ponta: cortam quem pisa de pe
    estatua: str = "espantalho"  # o que se vira quando voce nao olha: "espantalho" ou "boneca"
    cego_inicio: P | None = None
    agua: Callable[[float, float], int] | None = None  # 0 seco, 1 raso, 2 fundo
    nevoa: tuple[float, float, float] = (17 / 255, 18 / 255, 25 / 255)
    neblina_longe: float = 24.0
    mundo: MundoColisao3D | None = field(default=None, repr=False, compare=False)  # `montar_colisao`

    def montar_colisao(self) -> None:
        """O `MundoColisao3D` do cenario parado: circulos viram capsulas em pe, caixas viram AABB,
        do chao ate a altura de cada um (camada `CORPO`, e `VISAO` se for mais alto que
        `VISAO_MIN`). Chame de novo se `circulos`/`caixas` mudarem (o pesadelo poe o fogo)."""
        borda = TAMANHO + 6.0
        mundo = MundoColisao3D((-borda, -borda, borda, borda), tamanho_celula=4.0,
                               max_formas=len(self.circulos) + len(self.caixas) + 16)
        for c in self.circulos:
            x, z, r = c[0], c[1], c[2]
            alto = c[3] if len(c) > 3 else ALTO
            mundo.adicionar(Capsula((x, -1.0, z), (x, max(alto, _CORPO_MIN), z), r), _camada(alto))
        for c in self.caixas:
            x0, z0, x1, z1 = c[:4]
            alto = c[4] if len(c) > 4 else ALTO
            mundo.adicionar(AABB((x0, -1.0, z0), (x1, max(alto, _CORPO_MIN), z1)), _camada(alto))
        mundo.construir()
        self.mundo = mundo

    def chao(self, x: float, z: float) -> int:
        """0 terra seca, 1 agua rasa (ate a canela), 2 agua funda."""
        return self.agua(x, z) if self.agua is not None else 0


def _camada(alto: float) -> int:
    return CORPO | VISAO if alto >= VISAO_MIN else CORPO


HISTORIA = "Sua irma Ayame sumiu nesta floresta. Leve os 7 omamori ao santuario, ao norte, antes de amanhecer."


# O pesadelo (depois de um final): as noites de novo, espelhadas, pegando fogo, e com um segundo
# monstro que completa o primeiro -- fugir de um e se entregar ao outro.
PARES = {"floresta": "pequena", "arrozal": "fantoche", "aldeia": "vulto", "bambuzal": "pequena",
         "cemiterio": "imitadora", "escola": "fantoche"}
PARES_TEXTO = {
    "floresta": "Ele e a pequena: a luz segura ele e chama ela.",
    "arrozal": "O Cego e ela, a de luto: para ficar atras dela e preciso correr, e o Cego ouve.",
    "aldeia": "A falsa e ele: encarar ela e dar as costas para o escuro.",
    "bambuzal": "O Farejador e a pequena: no escuro voce pisa nos tocos e sangra; com luz, ela vem.",
    "cemiterio": "Ela, a de luto, e a falsa: ficar atras de uma e dar as costas para a outra.",
    "escola": "A pequena e ela, a de luto: apagar para uma, acender nas costas da outra.",
    "torii": "A roda: a mesma, com menos tempo para responder.",
}
FOGOS = 12
PESADELO_PEQUENA = 2  # no pesadelo a pequena vem cedo: no 2o omamori


def pesadelo(m: Mapa) -> Mapa:
    """A mesma noite, no pesadelo: o segundo monstro (`PARES`), o fogo e a nevoa vermelha."""
    m = dataclasses.replace(m, fogo=True, nevoa=(38 / 255, 16 / 255, 12 / 255), circulos=list(m.circulos),
                            luzes=list(m.luzes))
    quem = PARES.get(m.bioma)
    longe = max(m.marcos.values(), key=lambda p: math.hypot(p[0] - m.inicio[0], p[1] - m.inicio[1]),
                default=m.santuario)
    if quem == "pequena":
        m.tem_pequena, m.pequena_aparece = True, PESADELO_PEQUENA
    elif quem == "fantoche":
        m.tem_fantoche, m.fantoche_inicio = True, longe
    elif quem == "vulto":
        m.tem_vulto = True
    elif quem == "imitadora":
        m.tem_imitadora = True
    rng = random.Random(m.bioma)
    pontos = [p for t in m.trilhas for p in t]
    tentativas = 0
    while len(m.fogos) < FOGOS and pontos and tentativas < 400:  # ao lado das trilhas, longe do comeco
        tentativas += 1
        bx, bz = rng.choice(pontos)
        a = rng.uniform(0, 2 * math.pi)
        x, z = bx + math.cos(a) * rng.uniform(2.6, 4.5), bz + math.sin(a) * rng.uniform(2.6, 4.5)
        if math.hypot(x - m.inicio[0], z - m.inicio[1]) < 8.0 or abs(x) > m.limite - 1 or abs(z) > m.limite - 1:
            continue
        if m.chao(x, z) or any(math.hypot(x - a_, z - b_) < 5.0 for a_, b_ in m.fogos):
            continue
        if any(math.hypot(x - mx, z - mz) < 3.0 for mx, mz in m.marcos.values()):
            continue
        if any(c[0] - 1 < x < c[2] + 1 and c[1] - 1 < z < c[3] + 1 for c in m.caixas):
            continue
        m.fogos.append((x, z))
        m.circulos.append((x, z, 0.6))
        m.luzes.append(((x, 1.0, z), (1.6, 0.6, 0.15), 5.0))
    m.montar_colisao()
    return m


def geometria_fogo(m: Mapa) -> Malha:
    """O fogo: um tronco carbonizado e as chamas (emissivas), e brasas em volta."""
    rng = random.Random(m.bioma + "fogo")
    partes: list[Malha] = []
    for x, z in m.fogos:
        partes.append(bloco((x, 0, z), rng.uniform(1.2, 2.4), 0.3, 0.2, 0.3, (20, 14, 12)))
        for k in range(3):
            cor = ((255, 110, 20), (255, 160, 40), (255, 220, 120))[k]
            larg = 1.0 - k * 0.28
            partes.append(bloco((x + rng.uniform(-0.15, 0.15), 0, z + rng.uniform(-0.15, 0.15)),
                                rng.uniform(1.2, 2.2) - k * 0.35, larg, 0.05, larg * 0.8, cor, emissivo=True))
        for _ in range(6):
            bx, bz = x + rng.uniform(-1.4, 1.4), z + rng.uniform(-1.4, 1.4)
            partes.append(bloco((bx, 0, bz), 0.05, 0.12, 0.12, 0.12, (200, 60, 10), emissivo=True))
    return juntar(*partes)


def gerar(bioma: str) -> Mapa:
    """O mapa de uma noite pelo nome do bioma."""
    if bioma == "arrozal":
        from terror_ps1 import arrozal
        return arrozal.gerar_mapa()
    if bioma == "aldeia":
        from terror_ps1 import aldeia
        return aldeia.gerar_mapa()
    if bioma == "bambuzal":
        from terror_ps1 import bambuzal
        return bambuzal.gerar_mapa()
    if bioma == "rio":
        from terror_ps1 import rio
        return rio.gerar_mapa()
    if bioma == "torii":
        from terror_ps1 import torii
        return torii.gerar_mapa()
    if bioma == "escola":
        from terror_ps1 import escola
        return escola.gerar_mapa()
    if bioma == "cemiterio":
        from terror_ps1 import cemiterio
        return cemiterio.gerar_mapa()
    return gerar_mapa()


def gerar_mapa(semente: int = 7) -> Mapa:
    rng = random.Random(semente)
    m = Mapa(bioma="floresta", nome="a floresta", historia=HISTORIA, inicio=INICIO, santuario=SANTUARIO,
             limite=LIMITE, marcos=dict(MARCOS), nome_marco=dict(NOME_MARCO), trilhas=TRILHAS,
             esconderijos={k: (x, z, y, "seco") for k, (x, z, y) in ESCONDERIJOS.items()},
             altar_oitavo=ALTAR_OITAVO, arvore_outra=ARVORE_MORTA_OUTRA, amuleto_no_marco=dict(AMULETO_NO_MARCO),
             placas=list(PLACAS))
    for nome, (mx, mz) in MARCOS.items():
        dx, dz, y = AMULETO_NO_MARCO[nome]
        m.amuletos.append((mx + dx, mz + dz, y))
    _colisao_dos_marcos(m)

    jx, jz = MARCOS["jizo"]
    m.jizos = [(jx - 2.0 + k * 1.1, jz - 1.6) for k in range(6)]
    livres = [INICIO, SANTUARIO, ARVORE_MORTA_OUTRA] + list(MARCOS.values()) + [p for p, _ in PLACAS]
    raios = [5.0, 7.5, 4.5] + list(RAIO_MARCO.values()) + [1.2] * len(PLACAS)
    ocupado: dict[tuple[int, int], list[P]] = {}
    for _ in range(4200):  # arvores: longe das trilhas, dos marcos e umas das outras
        x, z = rng.uniform(-TAMANHO - 4, TAMANHO + 4), rng.uniform(-TAMANHO - 4, TAMANHO + 4)
        dentro = abs(x) < LIMITE + 1 and abs(z) < LIMITE + 1
        if dentro and (dist_trilha((x, z)) < 1.8 or any(math.hypot(x - a, z - b) < r for (a, b), r in zip(livres, raios))):
            continue
        cel = (int(x // 4), int(z // 4))
        vizinhos = [p for i in (-1, 0, 1) for j in (-1, 0, 1) for p in ocupado.get((cel[0] + i, cel[1] + j), ())]
        # espaco entre os troncos para enxergar longe; so a borda do mapa e uma parede fechada
        if any(math.hypot(x - a, z - b) < (ESPACO_ARVORES if dentro else 1.3) for a, b in vizinhos):
            continue
        ocupado.setdefault(cel, []).append((x, z))
        seca = rng.random() < 0.12
        m.arvores.append((x, z, rng.uniform(8.0, 13.0), seca))
        m.circulos.append((x, z, 0.35))
    for _ in range(70):  # pedras soltas
        x, z = rng.uniform(-LIMITE, LIMITE), rng.uniform(-LIMITE, LIMITE)
        if dist_trilha((x, z)) > 1.5 and all(math.hypot(x - a, z - b) > r for (a, b), r in zip(livres, raios)):
            r = rng.uniform(0.2, 0.7)
            m.pedras.append((x, z, r))
            if r > 0.35:
                m.circulos.append((x, z, r * 0.9, r * 0.6))  # baixa: segura, nao tapa a visao

    pontos = [(t, i) for t in TRILHAS for i in range(len(t) - 1)]
    while len(m.armadilhas) < 18:  # armadilhas: na trilha (ou rente a ela), longe do inicio e dos itens
        t, i = rng.choice(pontos)
        k = rng.random()
        a, b = t[i], t[i + 1]
        x = a[0] + (b[0] - a[0]) * k + rng.uniform(-0.7, 0.7)
        z = a[1] + (b[1] - a[1]) * k + rng.uniform(-0.7, 0.7)
        longe = [INICIO, SANTUARIO] + [(ax, az) for ax, az, _ in m.amuletos] + m.armadilhas
        if all(math.hypot(x - p[0], z - p[1]) > 4.0 for p in longe):
            m.armadilhas.append((x, z))
    while len(m.gravetos) < 80:  # gravetos secos: na trilha, onde se pisa sem olhar
        t, i = rng.choice(pontos)
        k = rng.random()
        a, b = t[i], t[i + 1]
        x = a[0] + (b[0] - a[0]) * k + rng.uniform(-0.9, 0.9)
        z = a[1] + (b[1] - a[1]) * k + rng.uniform(-0.9, 0.9)
        perto = [INICIO] + m.armadilhas + m.gravetos
        if all(math.hypot(x - p[0], z - p[1]) > (3.0 if p == INICIO else 1.2) for p in perto):
            m.gravetos.append((x, z))
    m.bilhetes = _bilhetes()
    m.paginas = list(LUGAR_PAGINAS[:len(PAGINAS)])
    for (ax, az), (bx, bz) in [((-12.0, 4.0), (-19.0, 2.0)), ((12.0, 0.0), (22.0, -5.0)), ((-4.0, 14.0), (0.0, 4.0)),
                               ((10.0, 27.0), (18.0, 23.0)), ((-10.0, -26.0), (-17.0, -22.5))]:
        m.pilhas.append(((ax + bx) / 2 + 1.3, (az + bz) / 2 + 0.8))  # pilhas: na beira da trilha

    m.luzes = [((SANTUARIO[0] - 1.6, 1.0, SANTUARIO[1] + 0.6), (1.5, 0.3, 0.15), 3.0),  # a vela do santuario
               ((-22.0, 1.4, 2.0), (1.1, 0.5, 0.2), 4.5),  # um lampiao esquecido na cabana
               ((-30.0, 0.4, -6.0), (1.3, 0.45, 0.12), 3.5),  # brasas no acampamento
               ((8.0, 0.5, -15.0), (1.0, 0.8, 0.4), 3.0)]  # velas dos jizo
    m.montar_colisao()
    return m


def _colisao_dos_marcos(m: Mapa) -> None:
    cx, cz = MARCOS["cabana"]  # paredes da cabana (porta no lado leste)
    m.caixas += [(cx - 2.1, cz - 1.6, cx + 2.1, cz - 1.4), (cx - 2.1, cz + 1.4, cx + 2.1, cz + 1.6),
                 (cx - 2.1, cz - 1.6, cx - 1.9, cz + 1.6), (cx + 1.9, cz - 1.6, cx + 2.1, cz - 0.5),
                 (cx + 1.9, cz + 0.5, cx + 2.1, cz + 1.6), (cx - 0.3, cz + 0.2, cx + 1.1, cz + 1.0, 0.85)]  # + a mesa
    px, pz = MARCOS["poco"]
    m.circulos.append((px, pz, 1.0, 0.9))
    sx, sz = MARCOS["pedras"]
    m.circulos += [(sx + 3.2 * math.cos(k * math.pi / 4), sz + 3.2 * math.sin(k * math.pi / 4), 0.45) for k in range(8)]
    jx, jz = MARCOS["jizo"]
    m.circulos += [(jx - 2.0 + k * 1.1, jz - 1.6, 0.3, 0.82) for k in range(6)]
    tx, tz = MARCOS["troncos"]
    m.caixas += [(tx - 3.0, tz - 0.3, tx + 2.5, tz + 0.3, 0.55), (tx - 1.5, tz + 1.2, tx + 3.0, tz + 1.7, 0.45)]
    ax, az = MARCOS["acampamento"]
    m.circulos += [(ax, az, 1.3, 1.6), (ax, az + 2.0, 0.55, 0.2)]  # a barraca e a fogueira
    sx, sz = SANTUARIO
    m.circulos += [(sx - 1.3, sz, 0.3), (sx + 1.3, sz, 0.3), (sx - 1.6, sz + 0.6, 0.33), (sx + 1.6, sz + 0.6, 0.33)]
    m.caixas.append((sx - 1.6, sz - 5.2, sx + 1.6, sz - 2.8))  # o santuario (honden)


# ------------------------------------------------------------------ geometria

MADEIRA, MADEIRA_ESCURA, PEDRA = (74, 56, 44), (46, 36, 30), (96, 94, 90)


def _pinheiro(x, z, alto, cor) -> Malha:
    """Pinheiro de floresta fechada: tronco alto e fino ate acima da cabeca, copa estreita
    so la em cima. Na altura dos olhos sobram os troncos -- e entre eles, a neblina."""
    partes = [bloco((x, 0, z), alto * 0.8, 0.26, 0.1, 0.26, (58, 44, 38))]
    base = max(2.6, alto * 0.38)
    for k in range(4):
        y = base + (alto - base) * k / 4
        r = (0.95 - 0.18 * k) * min(1.0, alto / 10)
        tom = tuple(min(255, int(c * (0.8 + 0.1 * k))) for c in cor)
        partes.append(cone((x, y, z), r, (alto - base) * 0.45, tom, lados=6, tampa=False))
    for k in range(2):  # galhinhos secos no tronco, na altura dos olhos
        b = (x, 1.4 + 0.6 * k, z)
        partes.append(bloco(b, b[1] + 0.5, 0.04, 0.01, 0.04, (58, 44, 38)).girada("z", 1.2 if k else -1.3, b))
    return juntar(*partes)


def _arvore_seca(x, z, alto) -> Malha:
    partes = [bloco((x, 0, z), alto, 0.3, 0.08, 0.3, (58, 50, 44))]
    for k, (y, ang, comp) in enumerate(((0.45, 0.9, 1.6), (0.6, -1.0, 1.3), (0.75, 0.7, 1.0))):
        base = (x, alto * y, z + (k - 1) * 0.05)
        partes.append(bloco(base, base[1] + comp, 0.1, 0.03, 0.1, (58, 50, 44)).girada("z", ang, base))
    return juntar(*partes)


def _cabana(x, z) -> Malha:
    partes = [bloco((x + (x0 + x1) / 2, 0, z + (z0 + z1) / 2), 2.4, x1 - x0, x1 - x0, z1 - z0, MADEIRA)
              for x0, z0, x1, z1 in [(-2.1, -1.6, 2.1, -1.4), (-2.1, 1.4, 2.1, 1.6), (-2.1, -1.6, -1.9, 1.6),
                                     (1.9, -1.6, 2.1, -0.5), (1.9, 0.5, 2.1, 1.6)]]
    partes += [bloco((x + 2.0, 2.0, z), 2.4, 0.2, 0.2, 1.0, MADEIRA),  # verga da porta
               bloco((x, 2.4, z), 3.4, 4.8, 0.25, 3.6, MADEIRA_ESCURA),  # o telhado
               bloco((x + 0.4, 0, z + 0.6), 0.85, 1.4, 1.4, 0.8, MADEIRA),  # a mesa
               bloco((x - 1.2, 0, z - 0.9), 0.5, 0.5, 0.5, 0.5, MADEIRA_ESCURA),  # um banco
               bloco((x - 0.2, 0.85, z + 0.6), 1.15, 0.12, 0.08, 0.12, (200, 150, 80), emissivo=True)]  # o lampiao
    return juntar(*partes)


def _poco(x, z) -> Malha:
    partes = [bloco((x + 0.85 * math.cos(a), 0, z + 0.85 * math.sin(a)), 0.9, 0.5, 0.45, 0.5, PEDRA)
              for a in (k * 2 * math.pi / 10 for k in range(10))]
    partes.append(bloco((x, -0.5, z), 0.05, 1.2, 1.2, 1.2, (8, 8, 10)))  # o buraco escuro
    partes += [bloco((x + dx, 0, z), 2.2, 0.14, 0.12, 0.14, MADEIRA) for dx in (-0.95, 0.95)]
    partes.append(bloco((x, 2.2, z), 2.65, 2.6, 0.2, 1.4, MADEIRA_ESCURA))
    return juntar(*partes)


def _arvore_morta(x, z) -> Malha:
    partes = [bloco((x, 0, z), 6.5, 0.9, 0.2, 0.8, (52, 44, 40))]
    galhos = [(2.6, 1.0, 2.6), (3.4, -1.1, 2.2), (4.3, 0.8, 1.8), (5.0, -0.7, 1.4)]
    for y, ang, comp in galhos:
        base = (x, y, z)
        partes.append(bloco(base, y + comp, 0.16, 0.04, 0.16, (52, 44, 40)).girada("z", ang, base))
        px, py = x - comp * 0.8 * math.sin(ang), y + comp * 0.8 * math.cos(ang)  # a ponta do galho girado
        partes.append(bloco((px, py - 1.1, z), py, 0.12, 0.12, 0.01, (196, 190, 176)))  # tiras de pano
    return juntar(*partes)


def _pedras(x, z) -> Malha:
    partes = [bloco((x + 3.2 * math.cos(k * math.pi / 4), 0, z + 3.2 * math.sin(k * math.pi / 4)), 1.7 + 0.4 * (k % 3),
                    0.7, 0.4, 0.5, PEDRA) for k in range(8)]
    return juntar(*partes, bloco((x, 0, z), 0.7, 1.4, 1.2, 1.0, (82, 80, 76)))  # o altar


def _jizo(x, z) -> Malha:
    """So as velas: as estatuas sao `malha_jizo`, desenhadas uma a uma (elas viram)."""
    return (bloco((x - 2.5, 0, z - 1.0), 0.15, 0.06, 0.06, 0.06, (240, 220, 160), emissivo=True)  # velas
            + bloco((x + 3.6, 0, z - 1.0), 0.12, 0.06, 0.06, 0.06, (240, 220, 160), emissivo=True))


def _troncos(x, z) -> Malha:
    partes = []
    for x0, zz, comp, larg in ((x - 3.0, z, 5.5, 0.55), (x - 1.5, z + 1.45, 4.5, 0.45)):
        base = (x0, larg / 2, zz)
        partes.append(bloco(base, base[1] + comp, larg, larg * 0.85, larg, MADEIRA_ESCURA).girada("z", -math.pi / 2, base))
    return juntar(*partes)


def _acampamento(x, z) -> Malha:
    lona = (70, 78, 64)
    partes = [bloco((x, 0, z), 1.6, 2.6, 0.1, 2.2, lona),  # a barraca caida
              bloco((x + 0.6, 0, z + 0.4), 0.9, 1.4, 0.1, 1.2, (56, 62, 52)).girada("z", 0.35, (x + 0.6, 0, z + 0.4))]
    for k in range(7):
        a = k * 2 * math.pi / 7
        partes.append(bloco((x + 0.5 * math.cos(a), 0, z + 2.0 + 0.5 * math.sin(a)), 0.15, 0.18, 0.15, 0.18, PEDRA))
    for k in range(3):
        partes.append(esfera((x - 0.15 + 0.15 * k, 0.07, z + 2.0 + 0.1 * (k - 1)), 0.08, (200, 70, 20), subdivisoes=0,
                             emissivo=True))
    return juntar(*partes)


def _placa(x, z) -> Malha:
    return bloco((x, 0, z), 1.3, 0.1, 0.1, 0.1, MADEIRA) + bloco((x, 1.0, z), 1.35, 0.8, 0.8, 0.05, MADEIRA)


def achatada(m: Malha, fator: float, teto: float | None = None) -> Malha:
    """Uma esfera virada monte: o que fica abaixo de y=0 vai para o chao, o resto encolhe em y
    por `fator` (e, com `teto`, nada passa dele)."""
    def f(p):
        p[:, 1] = np.maximum(p[:, 1], 0.0) * fator
        if teto is not None:
            p[:, 1] = np.minimum(p[:, 1], teto)
        return p
    return deformada(m, f)


def relevo_floresta() -> Relevo:
    """O chao da floresta como `Relevo` da engine (o mesmo que o `terreno` desenha)."""
    return Relevo.de_funcao(altura_terra, -TAMANHO - 4, TAMANHO + 4, -TAMANHO - 4, TAMANHO + 4, 0.6)


def geometria(m: Mapa) -> Malha:
    """Tudo que nao se mexe, numa malha so."""
    rng = random.Random(11)

    def terra(x, z):
        tom = rng.uniform(-7, 7)
        if dist_trilha((x, z)) < 1.1:
            return (int(80 + tom), int(74 + tom), int(64 + tom))
        if rng.random() < 0.2:
            return (int(44 + tom), int(52 + tom), int(36 + tom))  # musgo
        return (int(54 + tom), int(47 + tom), int(39 + tom))

    partes = [terreno(relevo_floresta(), terra)]
    for x, z, alto, seca in m.arvores:
        partes.append(_arvore_seca(x, z, alto * 0.75) if seca else _pinheiro(x, z, alto, (30, 40, 36)))
    for x, z, r in m.pedras:
        partes.append(achatada(esfera((x, 0.0, z), r, (78, 78, 74), subdivisoes=0), 0.6))
    rb = random.Random(5)
    for _ in range(300):  # moitas baixas (sem colisao)
        x, z = rb.uniform(-LIMITE, LIMITE), rb.uniform(-LIMITE, LIMITE)
        if dist_trilha((x, z)) > 1.3:
            partes.append(cone((x, 0, z), rb.uniform(0.3, 0.6), rb.uniform(0.3, 0.7), (34, 46, 34), lados=5, tampa=False))
    construtores = {"cabana": _cabana, "poco": _poco, "pedras": _pedras,  # a arvore morta anda: e malha a parte
                    "jizo": _jizo, "troncos": _troncos, "acampamento": _acampamento}
    for nome, (x, z) in MARCOS.items():
        if nome in construtores:
            partes.append(construtores[nome](x, z))
    sx, sz = SANTUARIO
    partes += [torii(sx, sz, (100, 30, 26), (64, 20, 18), inclina=math.radians(3)),
               lanterna(sx - 1.6, sz + 0.6, (110, 108, 104), (255, 70, 40)),
               lanterna(sx + 1.6, sz + 0.6, (110, 108, 104), (0, 0, 0), acesa=False, quebrada=True),
               bloco((sx, 0, sz - 4.0), 2.2, 3.2, 3.2, 2.4, MADEIRA_ESCURA),  # o santuario (honden)
               bloco((sx, 2.2, sz - 4.0), 3.0, 4.0, 0.3, 3.0, (40, 30, 28)),
               _placa(INICIO[0] + 1.5, INICIO[1] - 1.0)]
    for x, z, y, _ in m.bilhetes:  # o papel, branco-sujo, onde foi deixado
        y0 = y if y > 0.1 else altura_terra(x, z) + 0.02
        partes.append(bloco((x, y0, z), y0 + 0.012, 0.22, 0.22, 0.3, (196, 188, 168)))
    return juntar(*partes)


BILHETE_INICIO = ("SANTUARIO AO NORTE. Quem entrar depois do por do sol leve luz -- "
                  "e se ouvir um guizo, conte quantos amuletos ainda faltam.")
TEXTOS = {
    "cabana": "Diario do guarda, 3 de setembro. Mais uma crianca sumiu. Achamos so o omamori dela, aqui na "
              "mesa. O velho diz que a floresta conta, e que nao pode errar a conta.",
    "poco": "Joguei a lanterna no poco para ver o fundo. A luz desceu, desceu. La de baixo, alguem agradeceu.",
    "arvore_morta": "Cada fita e um nome. Amarramos para ele nao levar mais ninguem. Ele leva mesmo assim. "
                    "Se a arvore nao estiver aqui quando voce voltar, nao procure.",
    "pedras": "Nao reze em voz alta perto do circulo. Ele ouve tudo. Tudo, menos quem prende a respiracao.",
    "jizo": "Haru, Sora, Kenji, Mei, Ren, Yui. Seis jizos para seis criancas. Se contar sete, nao conte de novo.",
    "troncos": "Ayame correu para ca atras do guizo. Eu ouvi tambem. Nao tinha guizo nenhum aqui.",
    "acampamento": "Se a lanterna piscar perto dele, nao e a pilha. Ele mexe na luz. Ele aprende o que voce faz.",
}
# as paginas do diario achadas na floresta (o jogo mostra no TAB). A do mapa desenha o mapa -- e mente.
PAGINA_MAPA = 7
PAGINAS: list[tuple[str, str]] = [
    ("Antes de entrar", "Ayame sumiu ha tres noites. Ninguem quis vir comigo. Vou anotar tudo, porque se eu nao "
                        "voltar, alguem vai ter que vir depois."),
    ("A lanterna", "Apagada, ela recarrega. Acesa, ele me ve de longe. Apontada para ele, ele nao se mexe -- e a "
                   "pilha some."),
    ("O que ele ouve", "Correr, graveto, o omamori no bolso, a respiracao. Agachado e no escuro, eu sumo. Se os "
                       "grilos param, ele esta perto."),
    ("Esconderijos", "Atras da mesa da cabana, dentro do poco, na barraca caida. ESPACO entra e sai. Se ele me "
                     "viu entrar, nao adianta. Se ele chegar perto, prendo o ar."),
    ("A camera", "Seis fotos. O flash congela ele por uns segundos. Na foto aparece o que a floresta esconde. "
                 "Nao olhe as fotos por muito tempo."),
    ("Ayame", "Vi uma crianca correndo entre as arvores. Era o vestido dela. Ela nao me deixa chegar perto. "
              "As vezes ela leva a um omamori. As vezes, a uma armadilha."),
    ("A pequena", "Depois do quinto omamori apareceu outra coisa. Pequena. Ela so anda quando a luz esta nela. "
                  "Ele so anda quando a luz NAO esta nele. Nao existe jeito certo de segurar a lanterna."),
    ("O mapa", "Desenhei o que lembro. Confere com o que voce ve?"),
    ("Ultima pagina", "No altar havia oito omamori. Eu trouxe sete. Eu deixei o oitavo la. Nao sei o que "
                      "acontece com quem leva o oitavo de volta para a floresta."),
]
NOMES_JIZO = ["Haru", "Sora", "Kenji", "Mei", "Ren", "Yui", "(pedra lisa -- nenhum nome. ainda)", "Ayame"]


def _bilhetes() -> list[tuple[float, float, float, str]]:
    cx, cz = MARCOS["cabana"]
    px, pz = MARCOS["poco"]
    ax, az = MARCOS["arvore_morta"]
    sx, sz = MARCOS["pedras"]
    jx, jz = MARCOS["jizo"]
    tx, tz = MARCOS["troncos"]
    kx, kz = MARCOS["acampamento"]
    lugar = {"cabana": (cx + 0.6, cz + 0.5, 0.86), "poco": (px + 1.7, pz + 0.5, 0.0),
             "arvore_morta": (ax + 1.0, az + 0.4, 0.0), "pedras": (sx, sz, 0.71), "jizo": (jx + 3.0, jz - 0.6, 0.0),
             "troncos": (tx + 0.6, tz + 0.85, 0.0), "acampamento": (kx + 1.7, kz + 1.0, 0.0)}
    return [(INICIO[0] + 1.5, INICIO[1] - 0.6, 0.0, BILHETE_INICIO)] + [(*lugar[k], TEXTOS[k]) for k in TEXTOS]


def malha_jizo() -> Malha:
    """Uma estatua de jizo, olhando para +z (o jogo a gira)."""
    return juntar(bloco((0, 0, 0), 0.55, 0.36, 0.28, 0.3, PEDRA),
                  bloco((0, 0.4, 0.12), 0.56, 0.3, 0.34, 0.08, (150, 30, 30)),  # o babador vermelho
                  esfera((0, 0.68, 0), 0.14, PEDRA, subdivisoes=0))


def malha_arvore_morta() -> Malha:
    return _arvore_morta(0.0, 0.0)


def malha_placa() -> Malha:
    """Placa de madeira com ponta de seta, apontando para +z."""
    return juntar(bloco((0, 0, 0), 1.25, 0.09, 0.09, 0.09, MADEIRA),
                  bloco((0, 1.0, 0.05), 1.25, 0.05, 0.05, 0.7, MADEIRA),
                  bloco((0, 1.03, 0.45), 1.22, 0.05, 0.02, 0.16, MADEIRA))  # a ponta


def malha_pegada() -> Malha:
    """Uma pegada de bota na lama (sola e salto), apontando para +z."""
    lama = (30, 25, 21)
    return bloco((0, 0, 0.06), 0.012, 0.13, 0.13, 0.22, lama) + bloco((0, 0, -0.14), 0.012, 0.12, 0.12, 0.1, lama)


def malha_graveto(quebrado: bool) -> Malha:
    seco = (150, 132, 108)
    if quebrado:
        return (bloco((-0.16, 0.02, 0), 0.32, 0.03, 0.03, 0.03, seco).girada("z", 1.45, (-0.16, 0.02, 0))
                + bloco((0.12, 0.02, 0.03), 0.3, 0.03, 0.03, 0.03, seco).girada("z", -1.3, (0.12, 0.02, 0.03)))
    return (bloco((-0.3, 0.02, 0), 0.62, 0.035, 0.03, 0.035, seco).girada("z", -math.pi / 2, (-0.3, 0.02, 0))
            + bloco((0.05, 0.02, 0), 0.25, 0.025, 0.02, 0.025, seco).girada("z", -1.0, (0.05, 0.02, 0)))


def malha_olhos(cor=(200, 180, 120), afastados: float = 0.1, tamanho: float = 0.075) -> Malha:
    """Dois pontos que brilham (emissivos: a neblina nao os apaga), olhando para +z."""
    return juntar(*(bloco((dx, -tamanho / 2, 0), tamanho / 2, tamanho, tamanho, 0.01, cor, emissivo=True)
                    for dx in (-afastados, afastados)))


def malha_olhos_do_vulto() -> Malha:
    """Os olhos dele no escuro, onde ficam na cabeca tombada de `malhas.vulto`."""
    return movida(malha_olhos((255, 70, 40), 0.048, 0.05), -0.07, 2.4, 0.15)


def malha_rosto() -> Malha:
    """O rosto dele de perto (so quando ele te pega): comprido, palido, olhos fundos com um
    ponto de luz e a boca aberta demais. Olhando para +z, centrado na origem."""
    pele, fundo = (168, 160, 146), (10, 6, 6)
    partes = [escalada(esfera((0, 0, 0), 0.2, pele, subdivisoes=1), 0.95, 1.6, 0.75)]
    for dx in (-0.075, 0.075):
        partes.append(bloco((dx, 0.05, 0.13), 0.13, 0.07, 0.06, 0.04, fundo))  # as orbitas
        partes.append(bloco((dx, 0.085, 0.152), 0.1, 0.014, 0.014, 0.01, (255, 230, 200), emissivo=True))  # o ponto de luz
    partes.append(bloco((0, -0.24, 0.12), -0.04, 0.05, 0.09, 0.05, fundo))  # a boca, aberta ate o queixo
    return juntar(*partes)


def malha_pagina() -> Malha:
    """Uma folha de caderno caida no chao, com as linhas azuis."""
    return juntar(bloco((0, 0, 0), 0.01, 0.24, 0.24, 0.32, (214, 206, 186)),
                  *(bloco((0, 0.011, -0.1 + k * 0.06), 0.014, 0.2, 0.2, 0.008, (110, 130, 170)) for k in range(4)))


def malha_ayame() -> Malha:
    """Uma crianca de costas, correndo: yukata clara, cabelo preto ate os ombros. Olha para +z."""
    pano, cabelo, pele = (214, 208, 196), (14, 12, 12), (196, 170, 150)
    partes = [bloco((0, 0, 0), 0.75, 0.42, 0.22, 0.3, pano),  # a yukata, larga embaixo
              bloco((0, 0.75, 0), 0.95, 0.24, 0.2, 0.2, pano)]
    for dx in (-0.16, 0.16):
        partes.append(bloco((dx, 0.55, 0), 0.92, 0.05, 0.06, 0.06, pele).girada("z", 0.25 if dx > 0 else -0.25, (dx, 0.92, 0)))
    partes += [esfera((0, 1.08, 0), 0.13, pele, subdivisoes=0),
               bloco((0, 0.86, -0.05), 1.22, 0.3, 0.27, 0.2, cabelo),  # o cabelo cobrindo o rosto
               bloco((0, 0.5, 0.0), 0.56, 0.3, 0.3, 0.32, (150, 30, 34))]  # a faixa vermelha
    return juntar(*partes)


def malha_pequena() -> Malha:
    """A pequena: palida, encolhida de quatro, bracos compridos para a frente e a cabeca baixa. Olha para +z."""
    pele, escuro = (176, 168, 158), (14, 10, 10)
    partes = [bloco((0, 0.25, -0.1), 0.5, 0.34, 0.22, 0.5, pele)]  # as costas curvadas
    for dx in (-0.14, 0.14):
        partes.append(bloco((dx, 0, 0.18), 0.42, 0.04, 0.05, 0.05, pele).girada("z", 0.6, (dx, 0, 0.18)))  # bracos esticados
        partes.append(bloco((dx, 0, -0.3), 0.3, 0.05, 0.06, 0.06, pele).girada("z", -0.4, (dx, 0, -0.3)))  # pernas dobradas
    partes.append(escalada(esfera((0, 0.36, 0.24), 0.12, pele, subdivisoes=0), 1.0, 0.9, 1.1))
    partes += [bloco((dx, 0.36, 0.34), 0.4, 0.03, 0.03, 0.03, escuro) for dx in (-0.04, 0.04)]
    return juntar(*partes)


def malha_gota() -> Malha:
    """Uma gota de sangue no chao: uma mancha escura, irregular."""
    sangue = (150, 16, 18)
    return bloco((0, 0, 0), 0.006, 0.12, 0.12, 0.09, sangue) + bloco((0.05, 0, 0.04), 0.007, 0.05, 0.05, 0.06, sangue)


def malha_sinalizador() -> Malha:
    return (bloco((0, 0, 0), 0.05, 0.05, 0.05, 0.3, (200, 40, 30))
            + esfera((0, 0.06, 0.16), 0.06, (255, 90, 60), subdivisoes=0, emissivo=True))


def malha_amuleto() -> Malha:
    """O omamori: saquinho vermelho com faixa e cordao (centrado na origem)."""
    return juntar(bloco((0, -0.13, 0), 0.13, 0.18, 0.16, 0.05, (190, 30, 34)),
                  bloco((0, 0.0, 0), 0.05, 0.19, 0.17, 0.055, (220, 210, 190)),
                  bloco((0, 0.13, 0), 0.2, 0.03, 0.03, 0.03, (230, 200, 90)))


def malha_pilha() -> Malha:
    return bloco((0, 0, 0), 0.24, 0.1, 0.1, 0.1, (210, 170, 40)) + bloco((0, 0.24, 0), 0.27, 0.05, 0.05, 0.05, (30, 30, 30))


def malha_armadilha(fechada: bool) -> Malha:
    """A armadilha de urso: base, mola e duas mandibulas de dentes. Aberta, deitada no chao;
    fechada, as mandibulas em pe, mordendo o meio."""
    metal, dente, ferrugem = (88, 84, 78), (128, 122, 114), (86, 58, 42)
    partes = [bloco((0, 0, 0), 0.03, 0.22, 0.22, 0.22, ferrugem),
              bloco((-0.45, 0, 0), 0.03, 0.4, 0.4, 0.06, metal)]  # a mola
    for lado in (-1, 1):
        for k in range(7):
            a = math.pi * (k + 0.5) / 7
            if fechada:  # em pe: o arco no plano xy, dentes para o centro
                x, y = 0.32 * math.cos(a), 0.32 * math.sin(a)
                base = (x, y, 0.03 * lado)
                partes.append(bloco(base, y + 0.1, 0.04, 0.0, 0.02, dente).girada("z", a + math.pi / 2, base))
            else:  # deitada: o arco no chao, dentes para cima
                x, z = 0.32 * math.cos(a), 0.32 * math.sin(a) * lado
                partes.append(bloco((x, 0.02, z), 0.12, 0.04, 0.0, 0.03, dente))
        partes.append(bloco((0, 0, 0.3 * lado) if not fechada else (0, 0.3, 0.03 * lado), 0.04 if not fechada else 0.34,
                            0.64, 0.64, 0.04, metal))
    return juntar(*partes)

