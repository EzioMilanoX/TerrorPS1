# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""As regras do jogo (sem desenho): andar, a lanterna, o vulto e a floresta.

O blueprint SEN-04 L.A.N.T.E.R.N.: a luz segura o vulto -- iluminado, ele congela; no
escuro, ele anda. A pilha acaba e so recarrega apagada.

No mapa (`Estado(mapa=...)`) entra o resto:

* **Ele ouve e ve** (S.H.A.D.O.W.): so sabe onde voce esta pela lanterna acesa (que se ve
  de longe), pelo barulho (passos, gravetos, o guizo dos amuletos, a respiracao) ou de
  muito perto. Sem pista, ele procura.
* **O diretor de tensao** alterna caca e recuo: a tensao sobe com ele perto; no pico ele
  se afasta e a floresta fica calma por um tempo -- e e no calmo que ela mente.
* **Ele aprende**: quem gira a lanterna em volta de si o tempo todo o ensina a esperar a
  luz falhar. E o diretor sabe fazer a luz falhar na pior hora.
* **A floresta mente** (M.I.R.A.G.E.): fora da vista, os jizos se viram para voce, um a
  mais aparece, a arvore das fitas muda de lugar, as placas trocam de destino, surgem
  pegadas suas por onde voce nunca andou -- e o mapa do diario troca dois lugares.
* **v0.3**: esconderijos, a camera com flash, Ayame correndo ao longe, a pequena (que so
  anda NA luz), a noite que escurece e a chuva, o oitavo omamori (dois finais) e a noite
  seguinte (espelhada, e ele lembra).
"""
from __future__ import annotations

import dataclasses
import math
import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from terror_ps1.mapa import Mapa

ALTURA_OLHOS = 1.55
ABAIXADO = 0.6  # quanto os olhos descem agachado
VELOCIDADE = 2.2  # unidades por segundo
VEL_CORRER = 3.7
VEL_AGACHADO = 1.0
PESO_AMULETO = 0.07  # cada amuleto carregado tira 7% da velocidade
GIRO = 1.9  # radianos por segundo (teclado)
SENSIBILIDADE = 0.0024  # radianos por pixel (mouse)
INCLINA_MAX = 1.2
RAIO_JOGADOR = 0.3
PASSO_SOM = 0.85  # um som de passo a cada tanto andado
LIMITES = (-8.0, 10.0, -18.0, 7.0)  # sem mapa: x min, x max, z min, z max
INICIO = (2.5, 5.5)
VULTO_INICIO = (6.6, -8.5)
CONE_VULTO = math.radians(20)  # o vulto congela dentro deste angulo do feixe
ALCANCE_LUZ = 18.0
PASSO_VULTO = 1.4  # quanto ele anda a cada salto, no escuro
INTERVALO_VULTO = 1.1  # segundos entre saltos
PEGOU = 1.3  # distancia em que ele te alcanca
LONGE_DEMAIS = 24.0  # na caca: mais longe que isso, ele reaparece atras de voce
GASTO_PILHA = 1 / 75  # por segundo acesa (75 s de pilha cheia)
GASTO_ENCARAR = 1 / 30  # a mais, por segundo, com ele dentro do feixe
RECARGA_PILHA = 1 / 50  # por segundo apagada (o dinamo)
PEGAR_ITEM = 1.0  # distancia para pegar amuleto ou pilha
CARGA_PILHA = 0.5
ARMADILHA = 0.45  # distancia em que a armadilha fecha
PRESO = 3.0  # segundos presos (cada aperto de "soltar" tira um pouco)
FORCA_SOLTAR = 0.35
MANCANDO = 8.0  # segundos andando devagar depois de se soltar
CHEGOU_SANTUARIO = 2.5
GRAVETO = 0.4  # distancia em que o pe acha o graveto

# o que ele ouve (raio, em metros) e o que ele ve
RUIDO_PASSO = {"correndo": 16.0, "andando": 7.0, "agachado": 2.0}
RUIDO_TILINTAR = 1.6  # por amuleto carregado (metade agachado)
RUIDO_GRAVETO = 15.0
RUIDO_ARFAR = 12.0
RUIDO_RESPIRA = 5.5  # vezes o folego
VE_A_LUZ = 30.0  # a lanterna acesa se ve de longe
SENTE = 4.5  # perto assim, ele sabe
SEM_PISTA_MAX = 25.0  # sem pista por tanto tempo, a floresta conta para ele onde voce esta

# o folego
FOLEGO_SOBE = 0.22  # por segundo correndo
FOLEGO_DESCE = 0.1
RESPIRA_INTERVALO = 1.6
AR_DURA = 6.0  # segundos prendendo a respiracao
AR_VOLTA = 4.0
AR_SUBMERSO = 15.0  # embaixo d'agua o ar dura isto (e acaba sozinho)
FOLEGO_VOLTA = 0.4  # sem folego, so corre de novo com o folego abaixo disto

# o diretor de tensao
CACA_MAX = 80.0
RECUO = (18.0, 30.0)  # segundos de calma
INICIO_CALMO = 14.0
DISTANCIA_RECUO = 22.0
PISCA_DURA = (0.6, 1.3)
PISCA_ESPERA = 18.0
SINO_FALSO = (22.0, 40.0)
GIRANDO = 1.2  # rad/s em media: girar a lanterna em volta de si o tempo todo
SILENCIO = (13.0, 19.0)  # os bichos calam com ele mais perto que 13 m; voltam com ele a 19

JIZOS_A_MAIS = (3, 5)  # com tantos amuletos, aparece mais um jizo na fileira

# a vista (para a floresta saber quando pode mudar)
VISAO_METADE = math.radians(62)
VISAO_LONGE = 26.0

# o sinalizador
SINAL_DURA = 10.0
SINAL_RAIO = 16.0

# os esconderijos
ESCONDER = 1.9  # distancia para entrar
VIU_ENTRAR = 3.0  # s: se ele soube de voce ha tao pouco, ele viu voce entrar
ACHA_ESCONDIDO = 2.5  # perto assim, ele ouve quem nao prende o ar

# a camera
FILME = 6
FLASH_CONGELA = 3.0
FLASH_ALCANCE = 15.0
FLASH_CONE = math.radians(35)

# Ayame
AYAME_ESPERA = (35.0, 70.0)
AYAME_VEL = 3.2
AYAME_SOME = 7.0  # chegou perto assim, ela some
AYAME_DURA = 7.0
AYAME_LEVA_AO_AMULETO = 0.6  # o resto das vezes, a uma armadilha

# a pequena: o contrario dele -- so anda quando a luz esta nela
PEQUENA_APARECE = 5  # omamori
PEQUENA_PASSO = 0.9
PEQUENA_INTERVALO = 0.45
PEQUENA_PEGA = 1.0

# a noite
NOITE = 900.0  # em 15 min a lua se pos
CHUVA_COMECA = (240.0, 420.0)
CHUVA_DURA = (120.0, 200.0)
CHUVA_ABAFA = 0.4  # na chuva, os barulhos chegam a 40% da distancia

# a agua (os arrozais): devagar e barulhenta
VEL_AGUA = {1: 0.6, 2: 0.4}  # rasa, funda
RUIDO_AGUA = {1: 10.0, 2: 14.0}
AFUNDA_OLHOS = {1: 0.25, 2: 0.45}
SUBMERSO = -0.25  # os olhos, embaixo d'agua

# o Cego: enorme, lento, nao liga para luz -- e ouve tudo
CEGO_OUVIDO = 1.6  # ele ouve 60% mais longe que o vulto
CEGO_ANDA = 0.9
CEGO_CORRE = 2.7
CEGO_PEGA = 1.4
CEGO_PROCURA = 10.0  # sem som, ele vaga por perto de onde esta...
CEGO_DERIVA = 1 / 3  # ...puxando um terco do caminho para o seu lado (ele nao sabe onde: a area dele chega perto)

# as noites, em ordem; depois da ultima, recomecam espelhadas
FASES = ("floresta", "arrozal", "aldeia", "bambuzal")

# o Farejador (o bambuzal): so segue o seu sangue, gota por gota, na ordem em que caiu
SANGRA = 14.0  # segundos sangrando depois de um corte
GOTA_CADA = 0.7  # uma gota a cada tanto andado (parado, uma por segundo)
SANGUE_SECA = 75.0  # gota mais velha que isso ja nao cheira
TOCO = 0.35  # distancia em que o pe acha o toco
FAREJA_VEL = 1.9  # seguindo o rastro: mais devagar que voce andando, mais rapido que agachado
FAREJA_VAGA = 0.7
FAREJA_PEGA = 1.3

# a Imitadora (a aldeia): igual a Ayame. A de verdade foge; a falsa espera parada -- e se
# voce der as costas com ela perto, ela corre
IMITA_ESPERA = (14.0, 28.0)
IMITA_LONGE = (11.0, 16.0)  # onde ela aparece: na sua frente, no caminho
IMITA_ALCANCE = 12.0  # mais perto que isso, dar as costas e chamar
IMITA_CORRE = 3.6
IMITA_PEGA = 1.2
IMITA_VIDA = 25.0

# o fim
LEVOU_LONGE = 12.0  # levando o oitavo, longe assim do santuario a noite acaba do outro jeito


def direcao(giro: float, inclina: float = 0.0) -> tuple[float, float, float]:
    """Para onde se olha: giro 0 = para -z (para dentro da cena)."""
    c = math.cos(inclina)
    return (math.sin(giro) * c, math.sin(inclina), -math.cos(giro) * c)


@dataclass
class Estado:
    x: float = INICIO[0]
    z: float = INICIO[1]
    giro: float = 0.0
    inclina: float = -0.05
    passos: float = 0.0  # distancia andada (balanco da camera)
    pilha: float = 1.0
    acesa: bool = True
    vulto: tuple[float, float] = VULTO_INICIO
    relogio_vulto: float = 0.0
    pego: float = 0.0  # >0: tempo da tela de "ele chegou"
    tempo: float = 0.0
    feixe: tuple[float, float, float] = field(default_factory=lambda: direcao(0.0, -0.05))
    eventos: list[str] = field(default_factory=list)  # o que aconteceu neste passo (para o som)
    ultimo_passo: float = 0.0
    mapa: Mapa | None = None
    amuletos: list[tuple[float, float, float]] = field(default_factory=list)  # os que faltam
    pilhas: list[tuple[float, float]] = field(default_factory=list)
    armadilhas: list[list[float]] = field(default_factory=list)  # [x, z, fechada (0/1)]
    coletados: int = 0  # pegos ao todo (carregados + depositados)
    depositados: int = 0  # ja no santuario
    preso: float = 0.0
    mancando: float = 0.0
    venceu: bool = False
    # o corpo
    agachado: bool = False
    correndo: bool = False
    abaixar: float = 0.0  # 0 em pe, 1 agachado (suave)
    folego: float = 0.0  # 0 descansado, 1 ofegante
    ar: float = 1.0  # quanto ainda da para prender a respiracao
    segurando: bool = False
    sem_ar: bool = False  # arfou: so prende de novo com o ar de volta
    sem_folego: bool = False  # correu demais: so corre de novo descansado
    relogio_respira: float = 0.0
    # o vulto e o diretor
    fase: str = "caca"  # "caca" ou "recuo"
    relogio_fase: float = 0.0
    duracao_fase: float = CACA_MAX
    tensao: float = 0.0
    pista: tuple[float, float] | None = None  # onde ele acha que voce esta
    sem_pista: float = 0.0
    procura: tuple[float, float] | None = None  # para onde ele vai quando nao sabe
    vigilancia: float = 0.0  # quanto voce gira (rad/s, media)
    aprendeu: float = 0.0
    piscando: float = 0.0  # >0: a lanterna falhando de proposito
    espera_pisca: float = PISCA_ESPERA
    encarando: bool = False
    espera_sino: float = SINO_FALSO[0]
    quieta: bool = False  # a floresta calou
    # a luz extra
    sinalizadores: int = 0  # DESATIVADO (2026-11-12): sinalizador e diario no jogo fora por enquanto -- muita coisa para lembrar
    # sinalizadores: int = 1
    sinal: float = 0.0
    sinal_pos: tuple[float, float] | None = None
    olhos_falsos: list[tuple[float, float, float, float]] = field(default_factory=list)  # x, y, z, fase
    # a floresta que mente
    jizos: list[list[float]] = field(default_factory=list)  # [x, z, giro]
    placas: list[list] = field(default_factory=list)  # [x, z, alvo, giro]
    arvore_morta: tuple[float, float] | None = None
    pegadas: list[tuple[float, float, float]] = field(default_factory=list)  # x, z, giro
    rastro: list[tuple[float, float]] = field(default_factory=list)  # por onde voce andou
    gravetos: list[list[float]] = field(default_factory=list)  # [x, z, quebrado]
    mentiras: int = 0
    mentiu: bool = False  # ja mentiu neste recuo
    mapa_trocado: tuple[str, str] | None = None  # dois lugares trocados no mapa do diario
    # v0.3
    escondido: str | None = None  # o nome do esconderijo
    fora: tuple[float, float] | None = None  # onde voce estava antes de entrar
    achado: bool = False  # ele achou o esconderijo
    desde_pista: float = 99.0  # segundos desde a ultima vez que ele soube de voce
    filme: int = FILME
    flash: float = 0.0  # >0: o vulto ainda cego do flash
    ayame: list[float] | None = None  # [x, z, alvo x, alvo z, vida]
    espera_ayame: float = AYAME_ESPERA[0]
    pequena: tuple[float, float] | None = None
    relogio_pequena: float = 0.0
    relogio_noite: float = 0.0
    chuva: float = 0.0
    chuva_janela: tuple[float, float] = (1e9, 1e9)
    paginas: list[int] = field(default_factory=list)  # as do diario ja achadas
    paginas_no_chao: list[list[float]] = field(default_factory=list)  # [x, z, indice]
    oitavo: str = ""  # "" | "altar" | "levando"
    fim: str = ""  # "amanhecer" | "floresta"
    quem_pegou: str = ""
    # a noite seguinte (sobrevive ao recomeco)
    noite_n: int = 1
    espelho: bool = False
    aprendeu_base: float = 0.0
    memoria: dict = field(default_factory=dict)
    jizo_entrada: list[float] | None = None
    # trapacas (so pelo modo desenvolvedor do menu)
    dev: bool = False  # o modo desenvolvedor esta ligado (F2 radar, F3 ir, F4 acelerar)
    ultimo_ruido: tuple[float, float, float, float] | None = None  # x, z, raio, quando (para o radar)
    imortal: bool = False
    pilha_infinita: bool = False
    filme_infinito: bool = False
    # os arrozais
    espantalhos: list[list[float]] = field(default_factory=list)  # [x, z, giro]
    na_agua: int = 0
    cego: tuple[float, float] | None = None
    cego_alvo: tuple[float, float] | None = None
    cego_correndo: bool = False
    relogio_cego: float = 0.0
    # o bambuzal
    sangrando: float = 0.0
    sangue: list[list[float]] = field(default_factory=list)  # [x, z, quando] -- da mais velha a mais nova
    ultima_gota: float = 0.0  # `passos` na ultima gota
    relogio_gota: float = 0.0
    farejador: tuple[float, float] | None = None
    farejo_vaga: tuple[float, float] | None = None
    relogio_fareja: float = 0.0
    # a aldeia
    imitadora: list[float] | None = None  # [x, z, vida]
    espera_imita: float = IMITA_ESPERA[0]
    rng: random.Random = field(default_factory=lambda: random.Random(13), repr=False)

    def __post_init__(self) -> None:
        if self.mapa is not None and not self.amuletos and not self.coletados:
            m = self.mapa
            self.x, self.z = m.inicio
            self.vulto = (m.santuario[0], m.santuario[1] + 12.0)
            self.amuletos = list(self.mapa.amuletos)
            self.pilhas = list(self.mapa.pilhas)
            self.armadilhas = [[x, z, 0.0] for x, z in self.mapa.armadilhas]
            self.jizos = [[x, z, 0.0] for x, z in self.mapa.jizos]
            self.placas = [[x, z, alvo, _rumo((x, z), m.marcos[alvo])] for (x, z), alvo in m.placas]
            self.arvore_morta = m.marcos.get("arvore_morta")
            self.espantalhos = [[x, z, 0.0] for x, z in m.espantalhos]
            self.gravetos = [[x, z, 0.0] for x, z in self.mapa.gravetos]
            self.fase, self.duracao_fase = "recuo", INICIO_CALMO  # a noite comeca quieta
            # DESATIVADO (2026-11-12): sinalizador e diario no jogo fora por enquanto -- muita coisa para lembrar
            # self.paginas_no_chao = [[x, z, float(i)] for i, (x, z) in enumerate(self.mapa.paginas)]
            ini = self.rng.uniform(*CHUVA_COMECA)
            self.chuva_janela = (ini, ini + self.rng.uniform(*CHUVA_DURA))
            if not m.tem_vulto:  # nesta noite ele nao vem: so o calmo (e o que mais houver)
                self.vulto = (1e4, 1e4)
                self.duracao_fase = 1e9
            if m.tem_cego:
                self.cego = m.cego_inicio
            if m.tem_farejador:
                self.farejador = m.farejador_inicio

    @property
    def total_amuletos(self) -> int:
        return self.coletados + len(self.amuletos)

    @property
    def carregando(self) -> int:
        return self.coletados - self.depositados

    def olhos(self) -> tuple[float, float, float]:
        manca = 0.06 * abs(math.sin(self.passos * 2.75)) if self.mancando > 0 else 0.0
        balanco = (0.06 if self.correndo else 0.035) * math.sin(self.passos * 5.5)
        y = ALTURA_OLHOS - ABAIXADO * self.abaixar - 0.35 * (self.preso > 0) - manca + balanco
        if self.escondido == "submerso":
            y = SUBMERSO
        elif self.escondido:
            y = self.mapa.esconderijos[self.escondido][2]
        elif self.na_agua:
            y -= AFUNDA_OLHOS[self.na_agua]
        return (self.x, y, self.z)

    def luz_ligada(self) -> bool:
        return self.acesa and self.pilha > 0.0

    def iluminando(self, ponto: tuple[float, float, float]) -> bool:
        """O ponto esta dentro do feixe (e perto o bastante)? Lanterna falhando nao conta."""
        if not self.luz_ligada() or forca_da_luz(self) < 0.3:
            return False
        o = self.olhos()
        d = (ponto[0] - o[0], ponto[1] - o[1], ponto[2] - o[2])
        dist = math.sqrt(sum(c * c for c in d))
        if dist > ALCANCE_LUZ or dist < 1e-6:
            return False
        cos = sum(a * b for a, b in zip(d, self.feixe, strict=True)) / dist
        return cos > math.cos(CONE_VULTO)

    def na_vista(self, x: float, z: float) -> bool:
        """(x, z) pode estar na tela? Fora disso a floresta muda sem ninguem ver."""
        dx, dz = x - self.x, z - self.z
        d = math.hypot(dx, dz)
        if d > VISAO_LONGE:
            return False
        if d < 1.5:
            return True
        fx, _, fz = direcao(self.giro)
        return (dx * fx + dz * fz) / d > math.cos(VISAO_METADE)

    def de_frente(self, x: float, z: float) -> bool:
        """Voce esta virado para (x, z)? So o angulo, a qualquer distancia."""
        dx, dz = x - self.x, z - self.z
        d = math.hypot(dx, dz)
        if d < 1e-6:
            return True
        fx, _, fz = direcao(self.giro)
        return (dx * fx + dz * fz) / d > math.cos(VISAO_METADE)

    def dist_vulto(self) -> float:
        return math.hypot(self.x - self.vulto[0], self.z - self.vulto[1])

    def dist_cego(self) -> float:
        return math.hypot(self.x - self.cego[0], self.z - self.cego[1]) if self.cego else 1e9

    def dist_farejador(self) -> float:
        return math.hypot(self.x - self.farejador[0], self.z - self.farejador[1]) if self.farejador else 1e9

    def dist_imitadora(self) -> float:
        return math.hypot(self.x - self.imitadora[0], self.z - self.imitadora[1]) if self.imitadora else 1e9

    def dist_ameaca(self) -> float:
        """A distancia do monstro mais perto (o coracao, o silencio e a imagem suja usam esta)."""
        return min(self.dist_vulto(), self.dist_cego(), self.dist_imitadora(), self.dist_farejador())


def _rumo(de: tuple[float, float], para: tuple[float, float]) -> float:
    """O giro (em torno de y) que faz uma malha olhando para +z apontar de `de` para `para`."""
    return math.atan2(para[0] - de[0], para[1] - de[1])


def colidir(x: float, z: float, obstaculos: Sequence[tuple[float, float, float]],
            caixas: Sequence[tuple[float, float, float, float]] = (),
            limites: tuple[float, float, float, float] = LIMITES) -> tuple[float, float]:
    """Empurra o jogador (um circulo) para fora de cada obstaculo: circulos (x, z, raio) e
    caixas (x0, z0, x1, z1)."""
    for ox, oz, r in obstaculos:
        dx, dz = x - ox, z - oz
        d = math.hypot(dx, dz)
        minimo = r + RAIO_JOGADOR
        if d < minimo:
            if d < 1e-6:
                dx, dz, d = 1.0, 0.0, 1.0
            x, z = ox + dx / d * minimo, oz + dz / d * minimo
    for x0, z0, x1, z1 in caixas:
        px, pz = min(max(x, x0), x1), min(max(z, z0), z1)  # o ponto da caixa mais perto
        dx, dz = x - px, z - pz
        d = math.hypot(dx, dz)
        if d >= RAIO_JOGADOR:
            continue
        if d > 1e-6:
            x, z = px + dx / d * RAIO_JOGADOR, pz + dz / d * RAIO_JOGADOR
        else:  # o centro entrou na caixa: sai pela borda mais perto
            saidas = [(x - x0, x0 - RAIO_JOGADOR, z), (x1 - x, x1 + RAIO_JOGADOR, z),
                      (z - z0, x, z0 - RAIO_JOGADOR), (z1 - z, x, z1 + RAIO_JOGADOR)]
            _, x, z = min(saidas)
    lx0, lx1, lz0, lz1 = limites
    return min(max(x, lx0), lx1), min(max(z, lz0), lz1)


def atualizar(e: Estado, dt: float, frente: float, lado: float, girar: float, alternar_luz: bool,
              olhar: tuple[float, float] = (0.0, 0.0), obstaculos: Sequence[tuple[float, float, float]] = (),
              soltar: bool = False, correr: bool = False, agachar: bool = False, segurar_ar: bool = False,
              sinalizador: bool = False, foto: bool = False) -> None:
    """Um passo das regras. `frente`/`lado`/`girar` em -1..1; `olhar` = quanto o mouse andou
    (pixels); `obstaculos` = circulos extras que nao se atravessam (o mapa traz os seus);
    `soltar` = o botao de usar (forca a armadilha, entra e sai do esconderijo, deixa o oitavo
    no altar); `correr`, `agachar` e `segurar_ar` = botoes segurados; `sinalizador` e `foto`
    = apertou. Os eventos do passo (para o som) ficam em `e.eventos`."""
    e.tempo += dt
    e.eventos.clear()
    if e.pego > 0:
        e.pego -= dt
        if e.pego <= 0:
            reiniciar(e)
        return
    if e.pilha_infinita:
        e.pilha = 1.0
    if e.venceu:
        return
    e.relogio_noite += dt
    e.desde_pista += dt
    giro_antes = e.giro
    e.giro += girar * GIRO * dt + olhar[0] * SENSIBILIDADE
    e.inclina = min(max(e.inclina - olhar[1] * SENSIBILIDADE, -INCLINA_MAX), INCLINA_MAX)
    if dt > 0:  # quanto voce gira, em media nos ultimos ~6 s
        e.vigilancia += (abs(e.giro - giro_antes) / dt - e.vigilancia) * (1 - math.exp(-dt / 6.0))

    if soltar and e.preso <= 0 and e.mapa is not None:
        soltar = not _usar(e)  # perto de um esconderijo ou do altar, ESPACO e "usar"
    e.agachado = agachar and e.preso <= 0 and not e.escondido
    if e.sem_folego and e.folego < FOLEGO_VOLTA:
        e.sem_folego = False
    e.correndo = (correr and not e.agachado and frente > 0 and e.preso <= 0 and e.mancando <= 0 and not e.escondido
                  and not e.sem_folego)
    e.abaixar += ((1.0 if e.agachado else 0.0) - e.abaixar) * (1 - math.exp(-10 * dt))
    _andar(e, dt, frente, lado, soltar, obstaculos)

    k = 1 - math.exp(-8 * dt)  # o feixe segue o olhar com um pouco de atraso (a mao)
    alvo = direcao(e.giro, e.inclina)
    f = tuple(a + (b - a) * k for a, b in zip(e.feixe, alvo, strict=True))
    n = math.sqrt(sum(c * c for c in f))
    e.feixe = tuple(c / n for c in f)

    if alternar_luz:
        e.acesa = not e.acesa
        e.eventos.append("clique")
        e.olhos_falsos = _olhos_no_escuro(e) if not e.acesa and e.mapa is not None else []
    e.encarando = e.iluminando((e.vulto[0], 1.6, e.vulto[1]))
    if e.luz_ligada():
        e.pilha = max(0.0, e.pilha - (GASTO_PILHA + (GASTO_ENCARAR if e.encarando else 0.0)) * dt)
    elif not e.acesa:
        e.pilha = min(1.0, e.pilha + RECARGA_PILHA * dt)
    e.piscando = max(0.0, e.piscando - dt)

    if sinalizador and e.sinalizadores > 0 and e.sinal <= 0:
        e.sinalizadores -= 1
        e.sinal, e.sinal_pos = SINAL_DURA, (e.x, e.z)
        e.eventos.append("sinalizador")
        lembra = e.memoria.get("sinalizador", False) and e.noite_n > 1  # ja viu essa luz: congela, mas nao foge
        e.memoria["sinalizador"] = True
        if e.mapa is not None and e.dist_vulto() < SINAL_RAIO and not lembra:
            _fase(e, "recuo")  # ele foge da luz vermelha
    e.sinal = max(0.0, e.sinal - dt)

    if foto:
        _fotografar(e)
    e.flash = max(0.0, e.flash - dt)
    _respirar(e, dt, segurar_ar)
    if e.mapa is not None:
        _itens(e)
        _mentir(e)
        _silencio(e)
        _noite(e, dt)
        _ayame(e, dt)
        if e.mapa.tem_pequena:
            _pequena(e, dt)
        _cego(e, dt)
        if e.mapa.tem_imitadora:
            _imitadora(e, dt)
        if e.mapa.tem_farejador:
            _sangrar(e, dt)
            _farejador(e, dt)
    if e.mapa is None or e.mapa.tem_vulto:
        _vulto(e, dt)


# ------------------------------------------------------------------ o corpo

def _ouviu(e: Estado, raio: float) -> None:
    """Um barulho onde voce esta: se ele estiver dentro do raio, agora ele sabe."""
    raio *= 1.0 - (1.0 - CHUVA_ABAFA) * e.chuva  # a chuva cobre o barulho
    e.ultimo_ruido = (e.x, e.z, raio, e.tempo)
    if e.mapa is not None and e.dist_vulto() < raio:
        _soube(e)
    if e.cego is not None and e.dist_cego() < raio * CEGO_OUVIDO:  # o Cego corre para o som
        if not e.cego_correndo:
            e.eventos.append("cego_ouviu")  # so na virada: o gemido de quando ele ouve
        e.cego_alvo, e.cego_correndo = (e.x, e.z), True
        if e.escondido:
            e.achado = True


def _soube(e: Estado) -> None:
    """Ele sabe onde voce esta (e se voce esta escondido, achou o esconderijo)."""
    e.pista, e.sem_pista, e.desde_pista = (e.x, e.z), 0.0, 0.0
    if e.escondido:
        e.achado = True


def _andar(e: Estado, dt: float, frente: float, lado: float, soltar: bool, obstaculos) -> None:
    if e.escondido:
        e.folego = max(0.0, e.folego - FOLEGO_DESCE * dt)
        return
    if e.preso > 0:  # na armadilha: so sai com o tempo, mais rapido apertando "soltar"
        e.preso -= dt + (FORCA_SOLTAR if soltar else 0.0)
        if soltar:
            e.eventos.append("forca")
        if e.preso <= 0:
            e.preso = 0.0
            e.mancando = MANCANDO
        return
    e.mancando = max(0.0, e.mancando - dt)
    if e.correndo:
        vel = VEL_CORRER
    elif e.agachado:
        vel = VEL_AGACHADO
    else:
        vel = VELOCIDADE * (0.45 if e.mancando > 0 else 1.0)
    vel *= max(0.6, 1.0 - PESO_AMULETO * e.carregando)
    e.na_agua = e.mapa.chao(e.x, e.z) if e.mapa is not None else 0
    if e.na_agua:
        vel *= VEL_AGUA[e.na_agua]
    fx, _, fz = direcao(e.giro)
    dx = (fx * frente - fz * lado) * vel * dt
    dz = (fz * frente + fx * lado) * vel * dt
    if e.mapa is not None:
        lim = e.mapa.limite
        x, z = colidir(e.x + dx, e.z + dz, list(obstaculos) + e.mapa.circulos_perto(e.x, e.z) + _obstaculos_vivos(e),
                       e.mapa.caixas, (-lim, lim, -lim, lim))
    else:
        x, z = colidir(e.x + dx, e.z + dz, obstaculos)
    andou = math.hypot(x - e.x, z - e.z)
    e.passos += andou
    e.x, e.z = x, z
    e.folego = min(1.0, e.folego + FOLEGO_SOBE * dt) if e.correndo and andou > 0 else max(0.0, e.folego - FOLEGO_DESCE * dt)
    if e.folego >= 1.0 and not e.sem_folego:  # a stamina: o folego encheu, nao da mais para correr
        e.sem_folego = True
        e.eventos.append("sem_folego")
    if e.passos - e.ultimo_passo > PASSO_SOM:
        e.ultimo_passo = e.passos
        e.eventos.append("passo_agua" if e.na_agua else "passo")
        modo = "correndo" if e.correndo else "agachado" if e.agachado else "andando"
        raio = RUIDO_PASSO[modo]
        if e.na_agua:  # na agua, ate agachado espirra
            raio = max(raio, RUIDO_AGUA[e.na_agua] * (0.5 if e.agachado else 1.0))
        if e.carregando:
            e.eventos.append("tilinta")
            raio = max(raio, RUIDO_TILINTAR * e.carregando * (0.5 if e.agachado else 1.0))
        _ouviu(e, raio)
    if e.mapa is not None:
        if not e.rastro or math.hypot(e.x - e.rastro[-1][0], e.z - e.rastro[-1][1]) > 2.5:
            e.rastro = (e.rastro + [(e.x, e.z)])[-120:]
        if not e.agachado and e.mapa.tocos:  # de pe, o toco em ponta corta
            for tx, tz in e.mapa.tocos:
                if abs(e.x - tx) < TOCO and abs(e.z - tz) < TOCO and math.hypot(e.x - tx, e.z - tz) < TOCO:
                    _cortar(e)
                    break
        if not e.agachado:  # agachado, o pe acha o graveto antes de pisar
            for g in e.gravetos:
                if not g[2] and math.hypot(e.x - g[0], e.z - g[1]) < GRAVETO:
                    g[2] = 1.0
                    e.eventos.append("graveto")
                    _ouviu(e, RUIDO_GRAVETO)


def _obstaculos_vivos(e: Estado) -> list[tuple[float, float, float]]:
    """O que a floresta mudou de lugar tambem e solido: a arvore das fitas e os jizos a mais."""
    vivos = [(x, z, 0.3) for x, z, _ in e.jizos[len(e.mapa.jizos):]] if e.mapa is not None else []
    if e.cego is not None:
        vivos.append((*e.cego, 0.6))
    if e.arvore_morta is not None:
        vivos.append((*e.arvore_morta, 0.55))
    return vivos


def _respirar(e: Estado, dt: float, segurar: bool) -> None:
    if e.sem_ar and e.ar > 0.4:
        e.sem_ar = False
    if e.escondido == "submerso":  # embaixo d'agua o ar acaba sozinho (AR_SUBMERSO segundos)
        e.segurando = True
        e.ar -= dt / AR_SUBMERSO
        if e.ar <= 0:
            e.x, e.z = e.fora
            e.escondido, e.fora, e.achado = None, None, False
            e.ar, e.segurando, e.sem_ar, e.folego = 0.0, False, True, 1.0
            e.eventos += ["saiu", "arfou"]
            _ouviu(e, RUIDO_ARFAR)
        return
    e.segurando = segurar and not e.sem_ar and e.ar > 0
    if e.segurando:
        e.ar -= dt / AR_DURA
        if e.ar <= 0:  # nao aguentou: puxa o ar alto
            e.ar, e.segurando, e.sem_ar, e.folego = 0.0, False, True, 1.0
            e.eventos.append("arfou")
            _ouviu(e, RUIDO_ARFAR)
        return
    e.ar = min(1.0, e.ar + dt / AR_VOLTA)
    e.relogio_respira -= dt
    if e.folego > 0.25 and e.relogio_respira <= 0:  # ofegante: da para ouvir de perto
        e.relogio_respira = RESPIRA_INTERVALO * (1.2 - 0.5 * e.folego)
        e.eventos.append("respira")
        _ouviu(e, RUIDO_RESPIRA * e.folego)


def _itens(e: Estado) -> None:
    SANTUARIO = e.mapa.santuario  # noqa: N806 -- o santuario desta noite
    for a in list(e.amuletos):
        if math.hypot(e.x - a[0], e.z - a[1]) < PEGAR_ITEM:
            e.amuletos.remove(a)
            e.coletados += 1
            e.eventos.append("amuleto")
    for p in list(e.pilhas):
        if math.hypot(e.x - p[0], e.z - p[1]) < PEGAR_ITEM:
            e.pilhas.remove(p)
            e.pilha = min(1.0, e.pilha + CARGA_PILHA)
            e.eventos.append("pilha")
    for arm in e.armadilhas:
        if not arm[2] and e.preso <= 0 and math.hypot(e.x - arm[0], e.z - arm[1]) < ARMADILHA:
            arm[2] = 1.0
            e.preso = PRESO
            e.eventos.append("armadilha")
            if e.mapa.tem_farejador:
                _cortar(e)
            _vulto_ouviu(e)
            e.desde_pista = 0.0
    for pg in list(e.paginas_no_chao):
        if math.hypot(e.x - pg[0], e.z - pg[1]) < PEGAR_ITEM:
            e.paginas_no_chao.remove(pg)
            e.paginas.append(int(pg[2]))
            e.eventos.append("pagina")
    if math.hypot(e.x - SANTUARIO[0], e.z - SANTUARIO[1]) < CHEGOU_SANTUARIO:
        if e.carregando:  # deixa no altar o que trouxe: anda mais leve e para de tilintar
            e.depositados = e.coletados
            e.eventos.append("depositou")
        if not e.amuletos and e.coletados and not e.carregando and not e.oitavo:
            e.oitavo = "altar"  # no altar ha oito. Voce trouxe sete.
            e.eventos.append("oitavo")
            _fase(e, "recuo")
            e.duracao_fase = 1e9  # enquanto voce decide, ele espera
    _oitavo(e)


def _oitavo(e: Estado) -> None:
    """Os dois finais: deixar o oitavo no altar (ESPACO) e amanhecer, ou leva-lo de volta."""
    ALTAR_OITAVO, SANTUARIO = e.mapa.altar_oitavo, e.mapa.santuario  # noqa: N806
    if e.oitavo == "altar" and math.hypot(e.x - ALTAR_OITAVO[0], e.z - ALTAR_OITAVO[1]) < PEGAR_ITEM:
        e.oitavo = "levando"
        e.eventos.append("levou_oitavo")
    if e.oitavo == "levando" and math.hypot(e.x - SANTUARIO[0], e.z - SANTUARIO[1]) > LEVOU_LONGE:
        e.venceu, e.fim = True, "floresta"
        e.eventos.append("venceu")


def _usar(e: Estado) -> bool:
    """ESPACO fora da armadilha: entra/sai do esconderijo, ou deixa o oitavo. True se usou."""
    SANTUARIO = e.mapa.santuario  # noqa: N806
    if e.escondido:
        e.x, e.z = e.fora
        e.escondido, e.fora, e.achado = None, None, False
        e.eventos.append("saiu")
        return True
    if e.oitavo == "altar" and math.hypot(e.x - SANTUARIO[0], e.z - SANTUARIO[1]) < 4.0:
        e.venceu, e.fim = True, "amanhecer"
        e.eventos.append("venceu")
        return True
    if e.mapa.chao(e.x, e.z) == 2 and not e.sem_ar:  # na agua funda: afundar
        e.fora, e.escondido, e.achado = (e.x, e.z), "submerso", False
        e.eventos.append("afundou")
        return True
    for nome, (x, z, *_) in e.mapa.esconderijos.items():
        if math.hypot(e.x - x, e.z - z) < ESCONDER:
            e.fora = (e.x, e.z)
            e.x, e.z, e.escondido = x, z, nome
            viu = e.desde_pista < VIU_ENTRAR and e.dist_vulto() < VE_A_LUZ
            lembra = e.noite_n > 1 and nome in e.memoria.get("esconderijos", ())  # ele lembra da outra noite
            e.achado = viu or lembra
            usados = e.memoria.setdefault("esconderijos", [])
            if nome not in usados:
                usados.append(nome)
            e.eventos.append("escondeu")
            return True
    return False


def _fotografar(e: Estado) -> None:
    """O flash: cega ele por uns segundos se estiver na frente. Mas e luz -- e a pequena anda na luz."""
    if e.filme <= 0:
        e.eventos.append("sem_filme")
        return
    if not e.filme_infinito:
        e.filme -= 1
    e.eventos.append("foto")
    fx, _, fz = direcao(e.giro)
    for alvo, nome in ((e.vulto, "vulto"), (e.pequena, "pequena")):
        if alvo is None:
            continue
        dx, dz = alvo[0] - e.x, alvo[1] - e.z
        d = math.hypot(dx, dz)
        if 0 < d < FLASH_ALCANCE and (dx * fx + dz * fz) / d > math.cos(FLASH_CONE):
            if nome == "vulto":
                e.flash = FLASH_CONGELA
            else:  # a pequena avanca no clarao
                passo = min(2 * PEQUENA_PASSO, d - 0.2)
                e.pequena = (alvo[0] - dx / d * passo, alvo[1] - dz / d * passo)
                e.eventos.append("pequena_anda")
    if e.mapa is not None and not e.flash and e.dist_vulto() < VE_A_LUZ:
        _soube(e)  # o clarao se ve de longe


def _noite(e: Estado, dt: float) -> None:
    """A chuva vem no meio da noite, abafa tudo, e passa."""
    ini, fim = e.chuva_janela
    alvo = 1.0 if ini <= e.relogio_noite <= fim else 0.0
    antes = e.chuva
    e.chuva += (alvo - e.chuva) * min(1.0, dt / 8.0)
    if antes < 0.3 <= e.chuva:
        e.eventos.append("chuva")


def escuridao(e: Estado) -> float:
    """0 no comeco da noite; 1 quando a lua ja se pos."""
    return min(1.0, e.relogio_noite / NOITE)


def _ayame(e: Estado, dt: float) -> None:
    """Uma crianca correndo entre as arvores, longe. Ela leva voce a algum lugar."""
    if e.ayame is None:
        e.espera_ayame -= dt
        if e.espera_ayame > 0 or e.fase != "recuo" or not e.coletados or e.escondido:
            return
        e.espera_ayame = e.rng.uniform(*AYAME_ESPERA)
        a, d = e.giro + e.rng.uniform(-0.5, 0.5), e.rng.uniform(13.0, 17.0)
        x, z = e.x + math.sin(a) * d, e.z - math.cos(a) * d
        armadilhas = [(t[0], t[1]) for t in e.armadilhas if not t[2]]
        alvo = None
        if e.amuletos and (e.rng.random() < AYAME_LEVA_AO_AMULETO or not armadilhas):
            alvo = min(((a_[0], a_[1]) for a_ in e.amuletos), key=lambda p: math.hypot(p[0] - x, p[1] - z))
        elif armadilhas:
            alvo = min(armadilhas, key=lambda p: math.hypot(p[0] - x, p[1] - z))
        if alvo is None:
            return
        e.ayame = [x, z, alvo[0], alvo[1], AYAME_DURA]
        e.eventos.append("ayame")
        return
    x, z, tx, tz, vida = e.ayame
    vida -= dt
    d = math.hypot(tx - x, tz - z)
    if d > 1.5:
        passo = min(AYAME_VEL * dt, d - 1.5)
        x, z = x + (tx - x) / d * passo, z + (tz - z) / d * passo
    perto = math.hypot(e.x - x, e.z - z)
    if perto < AYAME_SOME or vida <= 0 or perto > 30.0:
        e.ayame = None
        e.eventos.append("ayame_some")
    else:
        e.ayame = [x, z, tx, tz, vida]


def _pequena(e: Estado, dt: float) -> None:
    """O contrario dele: so anda quando a luz esta nela."""
    if e.pequena is None:
        if e.coletados >= PEQUENA_APARECE:
            fx, _, fz = direcao(e.giro)
            e.pequena = (e.x - fx * 12.0, e.z - fz * 12.0)  # atras de voce
            e.eventos.append("pequena")
        return
    px, pz = e.pequena
    d = math.hypot(e.x - px, e.z - pz)
    if d > 30.0:
        fx, _, fz = direcao(e.giro)
        e.pequena = (e.x - fx * 12.0, e.z - fz * 12.0)
        return
    no_sinal = e.sinal > 0 and e.sinal_pos is not None and math.hypot(px - e.sinal_pos[0], pz - e.sinal_pos[1]) < SINAL_RAIO
    e.relogio_pequena += dt
    if (e.iluminando((px, 0.35, pz)) or no_sinal) and e.relogio_pequena >= PEQUENA_INTERVALO and d > 1e-6:
        e.relogio_pequena = 0.0
        passo = min(PEQUENA_PASSO, d)
        e.pequena = (px + (e.x - px) / d * passo, pz + (e.z - pz) / d * passo)
        e.eventos.append("pequena_anda")
    if math.hypot(e.x - e.pequena[0], e.z - e.pequena[1]) < PEQUENA_PEGA and not e.escondido:
        _pegar(e, "pequena")


def _cego(e: Estado, dt: float) -> None:
    """O Cego: anda sempre (luz nao muda nada), corre para cada som, e de resto vaga devagar,
    derivando para o seu lado. Se esbarrar em voce, acabou."""
    if e.cego is None:
        return
    cx, cz = e.cego
    if e.cego_alvo is None or math.hypot(e.cego_alvo[0] - cx, e.cego_alvo[1] - cz) < 0.6:
        a, lim = e.rng.uniform(0, 2 * math.pi), e.mapa.limite - 1.0
        bx, bz = cx + (e.x - cx) * CEGO_DERIVA, cz + (e.z - cz) * CEGO_DERIVA  # sem saber, ele deriva para o seu lado
        e.cego_alvo = (min(lim, max(-lim, bx + CEGO_PROCURA * math.cos(a))),
                       min(lim, max(-lim, bz + CEGO_PROCURA * math.sin(a))))
        e.cego_correndo = False
    tx, tz = e.cego_alvo
    d = math.hypot(tx - cx, tz - cz)
    passo = min((CEGO_CORRE if e.cego_correndo else CEGO_ANDA) * dt, d)
    if d > 1e-6:
        e.cego = (cx + (tx - cx) / d * passo, cz + (tz - cz) / d * passo)
    e.relogio_cego += dt
    if e.relogio_cego >= (0.45 if e.cego_correndo else 0.95):  # os passos pesados na agua: da para ouvir de onde
        e.relogio_cego = 0.0
        e.eventos.append("cego_passo")
    if e.dist_cego() < CEGO_PEGA and (not e.escondido or e.achado):
        _pegar(e, "cego")


def _cortar(e: Estado) -> None:
    if e.sangrando <= 0:
        e.eventos.append("corte")
        e.ultima_gota = e.passos - GOTA_CADA  # a primeira gota cai na hora
    e.sangrando = SANGRA


def _sangrar(e: Estado, dt: float) -> None:
    """Sangrando, voce deixa gotas pelo caminho (e uma por segundo, parado). Gota velha seca."""
    if e.sangue and e.tempo - e.sangue[0][2] > SANGUE_SECA:
        e.sangue = [g for g in e.sangue if e.tempo - g[2] <= SANGUE_SECA]
    if e.sangrando <= 0:
        return
    e.sangrando = max(0.0, e.sangrando - dt)
    e.relogio_gota += dt
    if e.passos - e.ultima_gota >= GOTA_CADA or e.relogio_gota >= 1.0:
        e.ultima_gota, e.relogio_gota = e.passos, 0.0
        x, z = e.fora if e.escondido and e.fora else (e.x, e.z)
        e.sangue.append([x, z, e.tempo])
    if e.sangrando <= 0:
        e.eventos.append("parou_de_sangrar")


def _farejador(e: Estado, dt: float) -> None:
    """A regra dele, so ela: segue as gotas na ordem em que cairam, lambendo uma por uma. Sem
    sangue, vaga devagar (derivando para o seu lado). Encostou, acabou."""
    if e.farejador is None:
        return
    fx, fz = e.farejador
    if e.sangue:
        tx, tz = e.sangue[0][0], e.sangue[0][1]
        vel = FAREJA_VEL
    else:
        if e.farejo_vaga is None or math.hypot(e.farejo_vaga[0] - fx, e.farejo_vaga[1] - fz) < 0.6:
            a, lim = e.rng.uniform(0, 2 * math.pi), e.mapa.limite - 1.0
            bx, bz = fx + (e.x - fx) * CEGO_DERIVA, fz + (e.z - fz) * CEGO_DERIVA
            e.farejo_vaga = (min(lim, max(-lim, bx + 8.0 * math.cos(a))), min(lim, max(-lim, bz + 8.0 * math.sin(a))))
        tx, tz = e.farejo_vaga
        vel = FAREJA_VAGA
    d = math.hypot(tx - fx, tz - fz)
    if d > 1e-6:
        passo = min(vel * dt, d)
        e.farejador = (fx + (tx - fx) / d * passo, fz + (tz - fz) / d * passo)
    if e.sangue and math.hypot(e.farejador[0] - tx, e.farejador[1] - tz) < 0.45:
        e.sangue.pop(0)  # lambeu
    e.relogio_fareja += dt
    if e.relogio_fareja >= (1.0 if e.sangue else 2.4):
        e.relogio_fareja = 0.0
        e.eventos.append("fareja")
    escondido_sem_rastro = e.escondido and not e.sangrando
    if e.dist_farejador() < FAREJA_PEGA and not escondido_sem_rastro:
        _pegar(e, "farejador")


def _imitadora(e: Estado, dt: float) -> None:
    """Ela aparece parada no seu caminho, olhando para voce, chorando. Enquanto voce olha,
    ela nao se mexe. De as costas com ela perto, e ela corre. Quem se esconde, ela esquece."""
    if e.imitadora is None:
        e.espera_imita -= dt
        if e.espera_imita > 0 or e.escondido:
            return
        for _ in range(12):  # um lugar livre na sua frente
            a, d = e.giro + e.rng.uniform(-0.4, 0.4), e.rng.uniform(*IMITA_LONGE)
            x, z = e.x + math.sin(a) * d, e.z - math.cos(a) * d
            lim = e.mapa.limite
            if abs(x) < lim and abs(z) < lim:
                cx, cz = colidir(x, z, e.mapa.circulos_perto(x, z), e.mapa.caixas, (-lim, lim, -lim, lim))
                if math.hypot(cx - x, cz - z) < 0.05:
                    e.imitadora = [x, z, IMITA_VIDA]
                    e.espera_imita = e.rng.uniform(*IMITA_ESPERA)
                    e.eventos.append("imitadora")
                    return
        return
    x, z, vida = e.imitadora
    vida -= dt
    d = e.dist_imitadora()
    if e.escondido or vida <= 0 or d > 30.0:  # ela esquece de quem some
        e.imitadora = None
        e.eventos.append("imitadora_some")
        return
    if not e.de_frente(x, z) and d < IMITA_ALCANCE:  # de costas para ela: ela corre
        passo = min(IMITA_CORRE * dt, d)
        x, z = x + (e.x - x) / d * passo, z + (e.z - z) / d * passo
        e.eventos.append("imitadora_corre")
    e.imitadora = [x, z, vida]
    if e.dist_imitadora() < IMITA_PEGA:
        if _pegar(e, "imitadora"):
            e.imitadora = None


def _pegar(e: Estado, quem: str) -> bool:
    """Alguem te alcancou. O unico lugar que marca "pego" -- e onde a trapaca de nao morrer
    atua. Devolve se pegou."""
    if e.imortal or e.pego > 0:
        return False
    e.pego, e.quem_pegou = 2.0, quem
    e.eventos.append("pegou")
    return True


def _vulto_ouviu(e: Estado) -> None:
    """O estalo de metal se ouve longe: o vulto corre metade do caminho ate o barulho, e a
    calma acaba."""
    vx, vz = e.vulto
    d = math.hypot(e.x - vx, e.z - vz)
    if d > 6.0:
        k = (d - max(6.0, d * 0.5)) / d
        e.vulto = (vx + (e.x - vx) * k, vz + (e.z - vz) * k)
    if e.mapa is not None:
        if e.fase != "caca":
            _fase(e, "caca")
        e.pista, e.sem_pista = (e.x, e.z), 0.0
        e.tensao = min(1.0, e.tensao + 0.25)


def _olhos_no_escuro(e: Estado) -> list[tuple[float, float, float, float]]:
    """Apagou a luz: olhos entre as arvores. Nao sao ele -- os dele sao vermelhos."""
    olhos = []
    for _ in range(4):
        a = e.giro + e.rng.uniform(-1.2, 1.2)
        d = e.rng.uniform(9.0, 20.0)
        olhos.append((e.x + math.sin(a) * d, e.rng.uniform(0.9, 2.2), e.z - math.cos(a) * d, e.rng.uniform(0, 6.3)))
    return olhos


def _silencio(e: Estado) -> None:
    """Grilos, sapos e corujas calam com ele perto -- e so voltam com ele bem mais longe."""
    d = e.dist_ameaca()
    if not e.quieta and d < SILENCIO[0]:
        e.quieta = True
        e.eventos.append("silencio")
    elif e.quieta and d > SILENCIO[1]:
        e.quieta = False


# ------------------------------------------------------------------ a floresta que mente

def _mentir(e: Estado) -> None:
    if not e.coletados:
        return  # ate o primeiro amuleto, a floresta e honesta
    for j in e.jizos + e.espantalhos + ([e.jizo_entrada] if e.jizo_entrada else []):  # viram quando voce nao olha
        if not e.na_vista(j[0], j[1]) and math.hypot(j[0] - e.x, j[1] - e.z) < 30.0:
            j[2] = _rumo((j[0], j[1]), (e.x, e.z))
    base = len(e.mapa.jizos)
    if base and any(e.coletados >= n and len(e.jizos) == base + k for k, n in enumerate(JIZOS_A_MAIS)):
        x0, z0 = e.mapa.jizos[0]
        novo = (x0 + 1.1 * len(e.jizos), z0)  # mais um na fileira
        if not e.na_vista(*novo) and not e.na_vista(x0, z0):
            e.jizos.append([novo[0], novo[1], _rumo(novo, (e.x, e.z))])
    if e.fase != "recuo" or e.mentiu:
        return
    mentira = ("pegadas", "placa", "arvore", "mapa")[e.mentiras % 4]
    if {"pegadas": _pegadas, "placa": _placa_mente, "arvore": _arvore_anda, "mapa": _mapa_mente}[mentira](e):
        e.mentiras += 1
        e.mentiu = True


def _pegadas(e: Estado) -> bool:
    """Pegadas suas saindo da trilha por onde voce passou -- para um lado onde voce nunca foi."""
    for i in range(len(e.rastro) - 2, 0, -1):
        (ax, az), (bx, bz) = e.rastro[i - 1], e.rastro[i]
        d = math.hypot(bx - e.x, bz - e.z)
        if 8.0 < d < 25.0 and not e.na_vista(bx, bz):
            lado = e.rng.choice((-1.0, 1.0))
            ang = math.atan2(bx - ax, bz - az) + lado * e.rng.uniform(1.1, 1.6)  # quase perpendicular
            ux, uz = math.sin(ang), math.cos(ang)
            novas = []
            for k in range(12):
                lad = 0.13 if k % 2 else -0.13
                novas.append((bx + ux * 0.7 * k + uz * lad, bz + uz * 0.7 * k - ux * lad, ang))
            e.pegadas = (e.pegadas + novas)[-36:]
            return True
    return False


def _mapa_mente(e: Estado) -> bool:
    """O mapa do diario troca dois lugares (se voce ja tem a pagina; senao, a vez passa)."""
    from terror_ps1.mapa import PAGINA_MAPA
    if PAGINA_MAPA in e.paginas:
        a, b_ = e.rng.sample(sorted(e.mapa.marcos), 2)
        e.mapa_trocado = (a, b_)
    return True


def _placa_mente(e: Estado) -> bool:
    if not e.placas:
        return True  # nao ha placas nesta noite: a vez passa
    fora = [p for p in e.placas if not e.na_vista(p[0], p[1]) and math.hypot(p[0] - e.x, p[1] - e.z) > 8.0]
    if not fora:
        return False
    p = e.rng.choice(fora)
    p[2] = e.rng.choice([k for k in e.mapa.marcos if k != p[2]])
    p[3] = _rumo((p[0], p[1]), e.mapa.marcos[p[2]])
    return True


def _arvore_anda(e: Estado) -> bool:
    """A arvore das fitas troca de lugar (e o amuleto dela, se ainda estiver la, vai junto)."""
    if e.arvore_morta is None or e.mapa.arvore_outra is None:
        return True  # nao ha arvore das fitas nesta noite
    lugares = (e.mapa.marcos["arvore_morta"], e.mapa.arvore_outra)
    if any(e.na_vista(*p) or math.hypot(p[0] - e.x, p[1] - e.z) < 12.0 for p in lugares):
        return False
    velho = e.arvore_morta
    novo = lugares[1] if velho == lugares[0] else lugares[0]
    dx, dz, y = e.mapa.amuleto_no_marco["arvore_morta"]
    if (velho[0] + dx, velho[1] + dz, y) in e.amuletos:
        e.amuletos[e.amuletos.index((velho[0] + dx, velho[1] + dz, y))] = (novo[0] + dx, novo[1] + dz, y)
    e.arvore_morta = novo
    return True


# ------------------------------------------------------------------ o vulto

def _fase(e: Estado, nome: str) -> None:
    e.fase, e.relogio_fase = nome, 0.0
    e.duracao_fase = e.rng.uniform(*RECUO) if nome == "recuo" else CACA_MAX
    e.pista = e.procura = None
    e.mentiu = False
    e.eventos.append(nome)


def _diretor(e: Estado, dt: float, d: float) -> None:
    """A curva do medo: sobe com ele perto, e no pico ele recua -- para o proximo pico doer."""
    e.relogio_fase += dt
    if e.vigilancia > GIRANDO:  # quem gira a luz em volta de si o tempo todo ensina ele a esperar
        e.aprendeu = min(1.0, e.aprendeu + dt / 20.0)
    else:
        e.aprendeu = max(0.0, e.aprendeu - dt / 90.0)
    if e.fase == "recuo":
        e.tensao = max(0.0, e.tensao - dt / 12.0)
        if e.relogio_fase > e.duracao_fase:
            _fase(e, "caca")
        return
    e.tensao = min(1.0, e.tensao + dt * max(0.0, (12.0 - d) / 12.0) / 9.0 + (dt * 0.04 if e.encarando else 0.0))
    if (e.tensao >= 1.0 and d > 3.0) or e.relogio_fase > e.duracao_fase:
        _fase(e, "recuo")
        return
    e.espera_pisca -= dt
    if e.encarando and d < 10.0 and e.espera_pisca <= 0:  # a luz falha bem na hora
        e.piscando = e.rng.uniform(*PISCA_DURA)
        e.espera_pisca = PISCA_ESPERA * (1.0 - 0.6 * e.aprendeu) * e.rng.uniform(0.7, 1.3)
        e.eventos.append("pisca")
    e.espera_sino -= dt
    if e.espera_sino <= 0 and 7.0 < d < 25.0 and not e.na_vista(*e.vulto):  # ele imita o guizo
        e.espera_sino = e.rng.uniform(*SINO_FALSO)
        e.eventos.append("sino_falso")


def _saber(e: Estado, d: float, dt: float) -> None:
    """O que ele sabe de voce: a luz acesa se ve de longe, e de perto ele sente."""
    if e.escondido and not e.achado:  # escondido: so a luz acesa ou a respiracao, de pertinho, te entregam
        if (e.luz_ligada() and d < VE_A_LUZ) or (d < ACHA_ESCONDIDO and not e.segurando):
            _soube(e)
        elif e.pista is None:
            e.sem_pista += dt
            if e.sem_pista > SEM_PISTA_MAX:  # ele vem conferir o esconderijo -- mas nao sabe se voce esta la
                e.pista, e.sem_pista = (e.x, e.z), 0.0
        return
    if (e.luz_ligada() and forca_da_luz(e) >= 0.3 and d < VE_A_LUZ) or d < SENTE:
        _soube(e)
    elif e.pista is None:
        e.sem_pista += dt
        if e.sem_pista > SEM_PISTA_MAX:  # sem pista por muito tempo, a floresta conta para ele
            e.pista, e.sem_pista = (e.x, e.z), 0.0


def _vulneravel(e: Estado) -> bool:
    return e.preso > 0 or not e.luz_ligada() or forca_da_luz(e) < 0.3


def _vulto(e: Estado, dt: float) -> None:
    d = e.dist_vulto()
    vx, vz = e.vulto
    no_sinal = e.sinal > 0 and e.sinal_pos is not None and math.hypot(vx - e.sinal_pos[0], vz - e.sinal_pos[1]) < SINAL_RAIO
    congelado = e.iluminando((vx, 1.6, vz)) or no_sinal or e.flash > 0
    if e.mapa is not None:
        _diretor(e, dt, d)
        _saber(e, d, dt)
    e.relogio_vulto += dt
    intervalo = INTERVALO_VULTO - 0.08 * e.coletados  # cada amuleto o deixa mais inquieto
    if e.relogio_vulto >= intervalo:
        e.relogio_vulto = 0.0
        if e.mapa is None:
            alvo, passo = (e.x, e.z), PASSO_VULTO
        elif e.fase == "recuo":
            alvo, passo = None, PASSO_VULTO
            if d < DISTANCIA_RECUO and d > 1e-6:  # se afasta, sem pressa
                alvo = (vx + (vx - e.x) / d * 3.0, vz + (vz - e.z) / d * 3.0)
        elif d > LONGE_DEMAIS:  # nunca longe demais: reaparece atras de voce
            fx, _, fz = direcao(e.giro)
            e.vulto = (e.x - fx * 16.0, e.z - fz * 16.0)
            alvo = None
        else:
            if e.pista is None and (e.procura is None or math.hypot(vx - e.procura[0], vz - e.procura[1]) < 1.0):
                a = e.rng.uniform(0, 2 * math.pi)  # procura: um ponto qualquer perto de voce
                e.procura = (e.x + 9.0 * math.cos(a), e.z + 9.0 * math.sin(a))
            alvo = e.pista or e.procura
            passo = PASSO_VULTO + 0.1 * e.coletados
            if e.aprendeu > 0.5 and d < 14.0:  # aprendeu: de perto, so anda quando voce falha -- e anda o dobro
                if not _vulneravel(e):
                    alvo = None
                passo *= 2.0
        if alvo is not None and not congelado:
            ax, az = alvo
            da = math.hypot(ax - vx, az - vz)
            if e.mapa is None:
                passo = min(passo, max(0.0, d - 0.5))
            else:
                passo = min(passo, da)
            if passo > 0 and da > 1e-6:
                e.vulto = (vx + (ax - vx) / da * passo, vz + (az - vz) / da * passo)
                e.eventos.append("vulto")
            if e.pista is not None and math.hypot(e.vulto[0] - e.pista[0], e.vulto[1] - e.pista[1]) < 1.0:
                e.pista = None  # chegou onde achava que voce estava
    if e.dist_vulto() < PEGOU and (not e.escondido or e.achado):
        _pegar(e, "vulto")


# ------------------------------------------------------------------ consultas (som e HUD)

def lado_de(e: Estado, x: float, z: float) -> float:
    """De que lado (x, z) esta, para o som: -1 esquerda, 1 direita, 0 na frente ou atras."""
    vx, vz = x - e.x, z - e.z
    d = math.hypot(vx, vz) or 1.0
    return (vx * math.cos(e.giro) + vz * math.sin(e.giro)) / d


def lado_do_vulto(e: Estado) -> float:
    return lado_de(e, *e.vulto)


def batimento(e: Estado) -> float:
    """Segundos entre batidas do coracao: 0 = nao bate (longe); mais perto, mais rapido."""
    d = e.dist_ameaca()
    return 0.0 if d > 9.0 else 0.38 + 0.07 * d


def amuleto_mais_perto(e: Estado) -> tuple[float, float, float] | None:
    if not e.amuletos:
        return None
    return min(e.amuletos, key=lambda a: math.hypot(e.x - a[0], e.z - a[1]))


def bilhete_perto(e: Estado) -> str | None:
    if e.mapa is None:
        return None
    for x, z, _, texto in e.mapa.bilhetes:
        if math.hypot(e.x - x, e.z - z) < 1.8:
            return texto if e.luz_ligada() else "(escuro demais para ler)"
    return None


def placa_perto(e: Estado) -> str | None:
    NOME_MARCO = e.mapa.nome_marco  # noqa: N806
    for x, z, alvo, _ in e.placas:
        if math.hypot(e.x - x, e.z - z) < 2.5 and e.luz_ligada():
            return f"a placa aponta para {NOME_MARCO[alvo]}"
    return None


def nome_do_jizo(e: Estado) -> str | None:
    """O nome escrito no jizo que voce ilumina de perto."""
    from terror_ps1.mapa import NOMES_JIZO
    if not e.luz_ligada():
        return None
    fx, _, fz = direcao(e.giro)
    jizos = list(enumerate(e.jizos)) + ([(len(NOMES_JIZO) - 1, e.jizo_entrada)] if e.jizo_entrada else [])
    for i, (x, z, _) in jizos:
        dx, dz = x - e.x, z - e.z
        d = math.hypot(dx, dz)
        if 0.3 < d < 3.5 and (dx * fx + dz * fz) / d > math.cos(math.radians(10)):
            return NOMES_JIZO[min(i, len(NOMES_JIZO) - 1)]
    return None


PERSISTE = ("mapa", "tempo", "eventos", "rng", "noite_n", "espelho", "aprendeu_base", "memoria", "jizo_entrada",
            "imortal", "pilha_infinita", "filme_infinito", "dev")


def reiniciar(e: Estado) -> None:
    """Recomeca a mesma noite (ele te pegou). O que e da noite seguinte fica."""
    novo = Estado(mapa=e.mapa)
    for f in dataclasses.fields(Estado):
        if f.name not in PERSISTE:
            setattr(e, f.name, getattr(novo, f.name))
    if e.noite_n > 1 and e.mapa is not None and e.mapa.tem_vulto:  # na noite seguinte ele ja sabe: sem calma
        e.aprendeu = e.aprendeu_base
        e.fase, e.duracao_fase = "caca", CACA_MAX


def bioma_da_noite(n: int) -> tuple[str, bool]:
    """Qual mapa e se espelhado: as FASES em ordem; depois da ultima, de novo, espelhadas."""
    return FASES[(n - 1) % len(FASES)], ((n - 1) // len(FASES)) % 2 == 1


def estado_da_noite(noite_n: int, aprendeu_base: float = 0.0, memoria: dict | None = None) -> Estado:
    """O comeco de uma noite qualquer (pelo menu, ou continuando a campanha): o mapa dela,
    espelhado ou nao, o jizo na entrada da floresta, e o que ele ja sabe de voce."""
    from terror_ps1 import mapa as m
    bioma, espelho = bioma_da_noite(noite_n)
    e = Estado(mapa=m.gerar(bioma))
    e.noite_n, e.espelho = noite_n, espelho
    e.aprendeu_base, e.memoria = aprendeu_base, dict(memoria or {})
    if noite_n > 1 and bioma == "floresta":
        ix, iz = e.mapa.inicio
        e.jizo_entrada = [ix - 1.8, iz - 3.0, 0.0]
    reiniciar(e)
    return e


def proxima_noite(e: Estado) -> None:
    """Depois de um final: a noite seguinte. Outro mapa (os arrozais; depois as mesmas noites
    espelhadas), um jizo na entrada da floresta, e ele lembra."""
    from terror_ps1 import mapa as m
    e.aprendeu_base = max(e.aprendeu, e.aprendeu_base, 0.6)
    e.noite_n += 1
    bioma, e.espelho = bioma_da_noite(e.noite_n)
    if e.mapa is not None and e.mapa.bioma != bioma:
        e.mapa = m.gerar(bioma)
    if e.mapa is not None and e.mapa.bioma == "floresta":
        ix, iz = e.mapa.inicio
        e.jizo_entrada = [ix - 1.8, iz - 3.0, 0.0]
    else:
        e.jizo_entrada = None
    reiniciar(e)


def forca_da_luz(e: Estado) -> float:
    """1 com pilha boa; com menos de 25%, a lanterna falha (pisca) cada vez mais. O diretor
    tambem a faz falhar de proposito (`piscando`)."""
    if not e.luz_ligada():
        return 0.0
    if e.piscando > 0:
        return 0.08 if math.sin(e.tempo * 47.0) * math.sin(e.tempo * 13.0) > -0.35 else 0.7
    if e.pilha > 0.25:
        return 1.0
    falha = math.sin(e.tempo * 31.0) * math.sin(e.tempo * 7.3) > e.pilha * 3.2 - 0.2
    return (0.15 if falha else 0.85) * (0.4 + 0.6 * e.pilha / 0.25)
