# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""A cena: a floresta em primeira pessoa, desenhada pelo `IRenderer3D` da engine com o
estilo PS1 (e a fita VHS que suja com ele perto), o HUD por cima com as primitivas 2D, e o
som -- metade do medo: passos, gravetos, a respiracao, o guizo do amuleto (e o falso), o
galho que ele quebra do lado em que ele esta, o coracao, e os grilos, sapos e corujas que
calam quando ele chega perto."""
from __future__ import annotations

import dataclasses
import math
import random
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np
from ouroboros.bootstrap.scene import IScene
from ouroboros.core.world import World
from ouroboros.interfaces.audio_engine import IAudioEngine
from ouroboros.interfaces.input_provider import IInputProvider
from ouroboros.interfaces.renderer import IRenderer
from ouroboros.interfaces.renderer3d import (
    COR_AFIM,
    Estilo3D,
    Iluminacao3D,
    Luz3D,
    translacao_e_giro_y,
    triangulos_para_arrays,
)

from terror_ps1 import aldeia, arrozal, bambuzal, malhas, mapa, progresso, regras, sons
from terror_ps1.malhas import _altura_terra

NEVOA = (17 / 255, 18 / 255, 25 / 255)  # cinza-azulado: os troncos escuros recortam contra ela
ESTILO_PS1 = Estilo3D(resolucao=(320, 180), tremor=True, modo_cor=COR_AFIM, fundo=NEVOA, neblina_cor=NEVOA,
                      neblina=(3.0, 24.0), bits_cor=5, pontilhado=True, grao=0.035, vinheta=0.8)
LUA = Luz3D("dir", (0.3, 0.8, -0.5), (0.07, 0.08, 0.13))
BRANCO = (230, 226, 218, 255)
AJUDA = "mouse olha   WASD anda   SHIFT corre   CTRL/C agacha   R prende o ar   F lanterna   ESC sai"
AJUDA_2 = "ESPACO usa (esconder, soltar, deixar)   V camera"
# DESATIVADO (2026-11-12): sinalizador e diario no jogo fora por enquanto -- muita coisa para lembrar
# AJUDA_2 = "ESPACO usa (esconder, soltar, deixar)   V camera   G sinalizador   TAB diario"
REGRA_DA_NOITE = {"floresta": "ele so anda quando a luz nao esta nele -- e ouve tudo",
                  "arrozal": "ele nao enxerga: a luz nao importa. so o silencio. fique nos diques.",
                  "aldeia": "a verdadeira foge de voce. a falsa espera. nao de as costas para ela.",
                  "bambuzal": "ele so segue o seu sangue. nao corte caminho pelo bambu."}
INTERVALO_SINO = 3.5
ALCANCE_GUIZO = 14.0  # o guizo do amuleto mais perto so se ouve a esta distancia
POEIRA = 220  # graos de poeira no ar: so aparecem dentro do feixe
GOTAS = 520  # a chuva
CAIXA_CHUVA = np.array([14.0, 9.0, 14.0])
ID_FOTO = 91_001  # a textura da ultima foto
NOME_NOITE = {2: "SEGUNDA NOITE", 3: "TERCEIRA NOITE", 4: "QUARTA NOITE"}
TINTA = (40, 34, 42, 255)
CAIXA_POEIRA = np.array([7.0, 3.0, 7.0])


def _quebrar(texto: str, largura: int) -> list[str]:
    linhas, linha = [], ""
    for palavra in texto.split():
        if linha and len(linha) + len(palavra) > largura:
            linhas.append(linha)
            linha = ""
        linha = f"{linha} {palavra}".strip()
    return linhas + [linha]


def _geometria(m: mapa.Mapa) -> list:
    """Os triangulos do que nao se mexe, pelo bioma da noite."""
    return {"arrozal": arrozal.geometria, "aldeia": aldeia.geometria,
            "bambuzal": bambuzal.geometria}.get(m.bioma, mapa.geometria)(m)


def _centro(r: IRenderer, x: float, y: float, texto: str, tam: int, cor) -> None:
    """Texto centrado em x, com o topo em y (o `draw_text` so ancora no centro ou nos cantos)."""
    r.draw_text(x, y + tam * 0.6, texto, tam, cor, anchor="center")


class TerrorScene(IScene):
    def __init__(self, entrada: IInputProvider, renderer: IRenderer, audio: IAudioEngine | None = None,
                 ao_sair: Callable[[], None] | None = None, pasta_sons: Path | None = None,
                 estado: regras.Estado | None = None, modo: str = "campanha") -> None:
        """`estado`: a noite a jogar (o menu monta); `modo`: "campanha" (a seguinte vem depois,
        e o progresso fica salvo) ou "livre" (uma noite solta, do modo desenvolvedor: no fim,
        volta ao menu). `ao_sair`: ESC -- volta ao menu."""
        self.entrada = entrada
        self.renderer = renderer
        self.audio = audio
        self.ao_sair = ao_sair
        self.modo = modo
        self.estado = estado or regras.Estado(mapa=mapa.gerar_mapa())
        self.mapa = self.estado.mapa
        self.r3d = renderer.renderer_3d()
        if self.r3d is None:
            raise RuntimeError('o jogo precisa do renderer "gl" (placa de video, ROADMAP M21 da engine)')
        self._malhas: list[int] = []  # tudo o que esta cena pos na placa de video (sai com ela)

        def malha(tris):
            return self._criar(*triangulos_para_arrays(tris))

        self.cenario = malha(_geometria(self.mapa))
        self.m_espantalho = malha(arrozal.malha_espantalho())
        self.m_cego = malha(arrozal.malha_cego())
        self.m_boneca = malha(aldeia.malha_boneca())
        self.m_farejador = malha(bambuzal.malha_farejador())
        self.m_gota = malha(mapa.malha_gota())
        self._passos_imita = 0.0
        self.vulto = malha(malhas.vulto(0.0, 0.0))
        self.m_amuleto = malha(mapa.malha_amuleto())
        self.m_pilha = malha(mapa.malha_pilha())
        self.m_armadilha = (malha(mapa.malha_armadilha(False)), malha(mapa.malha_armadilha(True)))
        self.m_jizo = malha(mapa.malha_jizo())
        self.m_arvore = malha(mapa.malha_arvore_morta())
        self.m_placa = malha(mapa.malha_placa())
        self.m_pegada = malha(mapa.malha_pegada())
        self.m_graveto = (malha(mapa.malha_graveto(False)), malha(mapa.malha_graveto(True)))
        self.m_olhos = malha(mapa.malha_olhos())
        self.m_olhos_vulto = malha(mapa.malha_olhos_do_vulto())
        self.m_rosto = malha(mapa.malha_rosto())
        self.m_sinal = malha(mapa.malha_sinalizador())
        self.m_pagina = malha(mapa.malha_pagina())
        self.m_ayame = malha(mapa.malha_ayame())
        self.m_pequena = malha(mapa.malha_pequena())
        rng_chuva = np.random.default_rng(9)
        self._gotas = rng_chuva.uniform(0, 1, (GOTAS, 3)) * CAIXA_CHUVA
        self._cor_gotas = np.full((GOTAS * 3, 3), (150.0, 160.0, 182.0))
        self.chuva = self._criar(*self._chuva(), dinamica=True)
        self._diario, self._pagina_vista = False, 0
        self._radar, self._acelerar, self._ir = False, False, -1  # ferramentas do modo desenvolvedor
        self._foto_pendente, self._foto_t, self._flash_t = False, -99.0, -99.0
        self._pasta_foto = Path(tempfile.gettempdir()) / "terror_ps1_fotos"
        self._som_chuva = 0.0
        self._chao = {}  # altura do terreno sob cada coisa pequena (calculada uma vez)
        self._sino = 0.0
        rng = np.random.default_rng(5)
        self._poeira_base = rng.uniform(0, 1, (POEIRA, 3)) * CAIXA_POEIRA
        self._poeira_vel = rng.uniform(-0.12, 0.12, (POEIRA, 3)) + (0.0, -0.04, 0.0)
        self._poeira_cores = np.full((POEIRA * 3, 3), (210.0, 204.0, 190.0))
        self.poeira = self._criar(*self._poeira(), dinamica=True)
        self._fps, self._ultimo = 0.0, time.perf_counter()
        self._coracao = 0.0
        self._grilos = 0.0
        self._bicho = 4.0
        self._rng = random.Random(3)
        self._tela_cheia = False
        self._venceu_em = 0.0
        entrada.set_mouse_captured(True)
        if audio is not None:
            self._sons = sons.gerar(pasta_sons or Path(tempfile.gettempdir()) / "terror_ps1_sons")
            for nome, caminho in self._sons.items():
                audio.load_sound(nome, str(caminho))
            audio.load_track("zumbido", str(self._sons["zumbido"]))
            audio.set_track_volume(0.45)
            audio.play_track("zumbido", loop=True)

    def _y(self, x: float, z: float) -> float:
        chave = (round(x, 2), round(z, 2))
        if chave not in self._chao:
            self._chao[chave] = _altura_terra(x, z)
        return self._chao[chave]

    def _chuva(self):
        """Riscos de chuva caindo numa caixa que anda com voce; quantos, depende de quanto chove."""
        s = self.estado
        n = max(1, int(GOTAS * s.chuva))
        centro = np.array([s.x, 0.0, s.z])
        p = self._gotas[:n].copy()
        p[:, 1] -= s.tempo * 9.0
        p = (p - centro + CAIXA_CHUVA / 2 * (1, 0, 1)) % CAIXA_CHUVA + centro - CAIXA_CHUVA / 2 * (1, 0, 1)
        if s.chuva < 0.02:
            p[:, 1] = -50.0  # sem chuva: as gotas ficam embaixo do chao
        risco = [[0, 0.32, 0], [-0.006, 0, 0], [0.006, 0, 0]]
        tri = np.repeat(p, 3, axis=0) + np.tile(risco, (n, 1))
        return tri.astype(np.float32), self._cor_gotas[:n * 3]

    def _criar(self, *args, **kw) -> int:
        malha_id = self.r3d.criar_malha(*args, **kw)
        self._malhas.append(malha_id)
        return malha_id

    def liberar(self) -> None:
        """Saindo para o menu: tira as malhas da placa de video, para o zumbido e solta o mouse."""
        for malha_id in self._malhas:
            self.r3d.remover_malha(malha_id)
        self._malhas.clear()
        if self.audio is not None:
            self.audio.stop_track("zumbido")
        self.entrada.set_mouse_captured(False)

    def _trocar_de_mapa(self) -> None:
        """A noite seguinte trouxe outro mapa: refaz a malha do que nao se mexe."""
        self.mapa = self.estado.mapa
        self.r3d.remover_malha(self.cenario)
        self._malhas.remove(self.cenario)
        self.cenario = self._criar(*triangulos_para_arrays(_geometria(self.mapa)))
        self._chao = {}

    def _lado(self, v: float) -> float:
        """O lado do som: na noite espelhada, a esquerda e a direita trocam junto com a imagem."""
        return -v if self.estado.espelho else v

    def _poeira(self):
        s = self.estado
        centro = np.array([s.x, regras.ALTURA_OLHOS, s.z])
        p = (self._poeira_base + self._poeira_vel * s.tempo - centro + CAIXA_POEIRA / 2) % CAIXA_POEIRA
        p = p + centro - CAIXA_POEIRA / 2  # a caixa de poeira anda com o jogador
        tri = np.repeat(p, 3, axis=0) + np.tile([[0, 0.03, 0], [-0.025, -0.02, 0], [0.025, -0.02, 0]], (POEIRA, 1))
        return tri.astype(np.float32), self._poeira_cores

    # ------------------------------------------------------------ logica
    def update(self, world: World, delta_time: float) -> None:
        e = self.entrada
        if e.is_action_pressed("sair") and self.ao_sair is not None:  # ESC: volta ao menu
            self.liberar()
            self.ao_sair()
            return
        if e.is_action_pressed("tela_cheia"):
            self._tela_cheia = not self._tela_cheia
            self.renderer.set_fullscreen(self._tela_cheia)

        def eixo(mais, menos):
            return float(e.is_action_held(mais)) - float(e.is_action_held(menos))

        s = self.estado
        if s.dev:
            self._ferramentas_dev()
        # DESATIVADO (2026-11-12): sinalizador e diario no jogo fora por enquanto -- muita coisa para lembrar
        # if e.is_action_pressed("diario"):
            # self._diario = not self._diario
        espelho = -1.0 if s.espelho else 1.0  # na noite espelhada, os comandos de lado trocam junto com a imagem
        dx, dy = e.get_mouse_delta()
        if self._diario:  # lendo, voce para -- ele nao
            if s.paginas:
                passo = int(e.is_action_pressed("tras")) - int(e.is_action_pressed("frente"))
                self._pagina_vista = (self._pagina_vista + passo) % len(s.paginas)
            frente = lado = girar = 0.0
            dx = dy = 0.0
        else:
            frente, lado = eixo("frente", "tras"), eixo("direita", "esquerda") * espelho
            girar = eixo("girar_dir", "girar_esq") * espelho
        regras.atualizar(s, delta_time * (4.0 if self._acelerar else 1.0), frente, lado, girar,
                         e.is_action_pressed("lanterna"),
                         olhar=(dx * espelho, dy), soltar=e.is_action_pressed("soltar"),
                         correr=e.is_action_held("correr"), agachar=e.is_action_held("agachar"),
                         segurar_ar=e.is_action_held("prender_ar"),
                         # DESATIVADO (2026-11-12): sinalizador e diario no jogo fora por enquanto -- muita coisa para lembrar
                         # sinalizador=e.is_action_pressed("sinalizador"),
                         foto=e.is_action_pressed("foto"))
        if "foto" in s.eventos:
            self._foto_pendente, self._flash_t = True, s.tempo
        if "pagina" in s.eventos:
            self._pagina_vista = len(s.paginas) - 1
        if s.venceu and not self._venceu_em:
            self._venceu_em = s.tempo
            self._concluiu()
        if s.venceu and e.is_action_pressed("soltar") and s.tempo - self._venceu_em > 2.0:
            if self.modo == "livre" and self.ao_sair is not None:  # noite solta: de volta ao menu
                self.liberar()
                self.ao_sair()
                return
            regras.proxima_noite(s)
        if s.mapa is not self.mapa:
            self._trocar_de_mapa()
        if not s.venceu:
            self._venceu_em = 0.0
        self._sons_do_passo(delta_time)

    def _ferramentas_dev(self) -> None:
        """F2 radar, F3 pula para o proximo lugar da noite (por ultimo, o santuario), F4 acelera x4."""
        e, s = self.entrada, self.estado
        if e.is_action_pressed("dev_radar"):
            self._radar = not self._radar
        if e.is_action_pressed("dev_acelerar"):
            self._acelerar = not self._acelerar
        if e.is_action_pressed("dev_ir") and not s.escondido:
            lugares = list(self.mapa.marcos.values()) + [self.mapa.santuario]
            self._ir = (self._ir + 1) % len(lugares)
            x, z = lugares[self._ir]
            lim = self.mapa.limite
            s.x, s.z = regras.colidir(x + 2.0, z + 2.0, self.mapa.circulos_perto(x + 2.0, z + 2.0), self.mapa.caixas,
                                      (-lim, lim, -lim, lim))

    def _desenhar_radar(self, r: IRenderer, w: float) -> None:
        """O radar do modo desenvolvedor: o mapa de cima, voce, os monstros e o ultimo barulho."""
        s, m = self.estado, self.mapa
        lado, x0, y0 = 220.0, w - 236.0, 34.0
        k = lado / 80.0

        def p(x, z):
            return x0 + (x + 40.0) * k, y0 + (z + 40.0) * k

        r.draw_ui_rect(x0, y0, lado, lado, (0, 0, 0, 170))
        for trilha in m.trilhas:
            for a, b in zip(trilha, trilha[1:], strict=False):
                r.draw_ui_line(*p(*a), *p(*b), (90, 84, 70, 200))
        for x, z in m.marcos.values():
            r.draw_ui_circle(*p(x, z), 3, (150, 150, 150, 220))
        r.draw_ui_circle(*p(*m.santuario), 4, (200, 50, 40, 255))
        for gx, gz, _ in s.sangue:
            r.draw_ui_circle(*p(gx, gz), 1, (150, 20, 20, 255))
        if s.ultimo_ruido and s.tempo - s.ultimo_ruido[3] < 1.5:  # ate onde o ultimo barulho chegou
            rx, rz, raio, _ = s.ultimo_ruido
            r.draw_ui_circle(*p(rx, rz), max(2, raio * k), (240, 220, 120, 160), 1)
        monstros = [("vulto", s.vulto if m.tem_vulto else None, (220, 40, 40)), ("cego", s.cego, (230, 140, 40)),
                    ("imitadora", s.imitadora[:2] if s.imitadora else None, (240, 200, 220)),
                    ("farejador", s.farejador, (150, 30, 30)), ("pequena", s.pequena, (170, 110, 230)),
                    ("ayame", s.ayame[:2] if s.ayame else None, (120, 220, 230))]
        for nome, pos, cor in monstros:
            if pos is not None:
                px, py = p(*pos)
                r.draw_ui_circle(px, py, 4, (*cor, 255))
                r.draw_text(px + 6, py - 6, nome, 10, (*cor, 255))
        px, py = p(s.x, s.z)
        fx, _, fz = regras.direcao(s.giro)
        r.draw_ui_line(px, py, px + fx * 10, py + fz * 10, (255, 255, 255, 255), 2)
        r.draw_ui_circle(px, py, 3, (255, 255, 255, 255))
        r.draw_text(x0, y0 + lado + 4, f"F2 radar  F3 ir  F4 x4{'  (ACELERADO)' if self._acelerar else ''}", 11,
                    (200, 80, 70, 230))

    def _concluiu(self) -> None:
        """Terminou a noite: marca como concluida e, na campanha, salva a noite seguinte (com o
        que ele ja sabe de voce) -- fechar o jogo agora continua dali."""
        s = self.estado
        try:
            progresso.marcar_concluida(s.mapa.bioma, s.espelho)
            if self.modo == "campanha":
                progresso.salvar_campanha(s.noite_n + 1, max(s.aprendeu, s.aprendeu_base, 0.6), s.memoria)
        except OSError:
            pass  # sem onde salvar, o jogo segue

    def _sons_do_passo(self, dt: float) -> None:
        a, s = self.audio, self.estado
        if a is None:
            return
        dist = s.dist_vulto()
        for ev in s.eventos:
            if ev == "passo_agua":
                a.play_one_shot("agua", (0.6 if s.correndo else 0.25 if s.agachado else 0.4) + 0.1 * self._rng.random())
            elif ev == "afundou":
                a.play_one_shot("agua", 0.7)
            elif ev == "cego_passo" and s.cego is not None:  # os passos dele: pesados, na agua, do lado dele
                d = s.dist_cego()
                vol = min(1.0, 4.0 / max(d, 1.0)) * (1.3 if s.cego_correndo else 1.0)
                a.play_spatial("cego_passo", min(1.0, vol), self._lado(regras.lado_de(s, *s.cego)))
            elif ev == "cego_ouviu" and s.cego is not None:
                a.play_spatial("gemido", min(1.0, 6.0 / max(s.dist_cego(), 1.0)), self._lado(regras.lado_de(s, *s.cego)))
            elif ev == "imitadora" and s.imitadora is not None:  # ela chora, parada, do lado em que esta
                d = s.dist_imitadora()
                a.play_spatial("choro", min(0.8, 4.0 / max(d, 1.0)), self._lado(regras.lado_de(s, *s.imitadora[:2])))
            elif ev == "imitadora_corre" and s.imitadora is not None and s.tempo - self._passos_imita > 0.3:
                self._passos_imita = s.tempo  # os passinhos dela, rapidos, atras de voce
                d = s.dist_imitadora()
                a.play_spatial("passinhos", min(1.0, 5.0 / max(d, 1.0)), self._lado(regras.lado_de(s, *s.imitadora[:2])))
            elif ev == "corte":
                a.play_one_shot("corte", 0.8)
            elif ev == "fareja" and s.farejador is not None:  # ele farejando: do lado dele, mais alto perto
                d = s.dist_farejador()
                a.play_spatial("farejar", min(1.0, 5.0 / max(d, 1.0)), self._lado(regras.lado_de(s, *s.farejador)))
            elif ev == "passo":
                base = 0.5 if s.correndo else 0.1 if s.agachado else 0.28
                a.play_one_shot("passo", base + 0.1 * self._rng.random())
            elif ev == "tilinta":
                a.play_one_shot("tilintar", (0.08 if s.agachado else 0.16) + 0.03 * s.carregando)
            elif ev == "graveto":
                a.play_one_shot("graveto", 0.9)
            elif ev == "respira":
                a.play_one_shot("respiracao", 0.15 + 0.35 * s.folego)
            elif ev == "arfou":
                a.play_one_shot("arfar", 0.9)
            elif ev == "clique":
                a.play_one_shot("clique", 0.5)
            elif ev == "vulto":  # a pista justa: o som vem do lado em que ele esta (a chuva abafa)
                a.play_spatial("galho", min(1.0, 2.5 / max(dist, 1.0)) * (1 - 0.7 * s.chuva),
                               self._lado(regras.lado_do_vulto(s)))
            elif ev == "sino_falso":  # ele imita o guizo: do lado dele, igualzinho ao de verdade
                a.play_spatial("sino", min(0.8, 2.0 / max(dist * 0.6, 1.0)), self._lado(regras.lado_do_vulto(s)))
            elif ev == "foto":
                a.play_one_shot("foto", 0.8)
            elif ev == "sem_filme":
                a.play_one_shot("clique", 0.3)
            elif ev in ("escondeu", "saiu"):
                a.play_one_shot("esconder", 0.5)
            elif ev == "pagina":
                a.play_one_shot("esconder", 0.3)
            elif ev == "ayame" and s.ayame is not None:
                d = math.hypot(s.ayame[0] - s.x, s.ayame[1] - s.z)
                a.play_spatial("passinhos", min(0.6, 3.0 / max(d, 1.0)), self._lado(regras.lado_de(s, *s.ayame[:2])))
            elif ev == "pequena_anda" and s.pequena is not None:
                d = math.hypot(s.pequena[0] - s.x, s.pequena[1] - s.z)
                a.play_spatial("estalos", min(1.0, 3.0 / max(d, 1.0)), self._lado(regras.lado_de(s, *s.pequena)))
            elif ev in ("oitavo", "levou_oitavo"):
                a.play_one_shot("sino", 0.7)
            elif ev == "pisca":
                a.play_one_shot("chiado", 0.5)
            elif ev == "sinalizador":
                a.play_one_shot("sinalizador", 0.7)
            elif ev == "pegou":
                a.play_one_shot("pegou", 0.9)
            elif ev in ("amuleto", "pilha", "depositou"):
                a.play_one_shot("coleta", 0.6)
            elif ev == "armadilha":
                a.play_one_shot("armadilha", 1.0)
            elif ev == "forca":
                a.play_one_shot("forca", 0.4)
            elif ev == "venceu":
                a.play_one_shot("amanhecer" if s.fim == "amanhecer" else "passinhos", 0.8)
        vivo = not s.venceu and s.pego <= 0
        seco = s.chuva < 0.3  # na chuva os bichos se calam -- e a pista do silencio some
        self._grilos -= dt
        if self._grilos <= 0:  # a noite viva: grilos (ou o coro de sapos nos arrozais) -- e calam quando ele chega
            arrozais = self.mapa.bioma == "arrozal"
            self._grilos += 2.0 if arrozais else 1.0
            if not s.quieta and vivo and seco:
                a.play_one_shot("sapos" if arrozais else "grilos", 0.3 if arrozais else 0.22)
        self._som_chuva -= dt
        if self._som_chuva <= 0:
            self._som_chuva += 1.8
            if s.chuva > 0.05:
                a.play_one_shot("chuva", 0.55 * s.chuva)
        self._bicho -= dt
        if self._bicho <= 0:
            self._bicho = self._rng.uniform(5.0, 14.0)
            if not s.quieta and vivo and seco:
                bicho = self._rng.choice(("sapo", "sapo", "coruja"))
                a.play_spatial(bicho, self._rng.uniform(0.12, 0.3), self._rng.uniform(-1, 1))
        self._sino -= dt
        alvo = regras.amuleto_mais_perto(s)
        if alvo is not None and self._sino <= 0:  # o guizo do amuleto mais perto: de que lado ele esta
            self._sino = INTERVALO_SINO
            d = math.hypot(s.x - alvo[0], s.z - alvo[1])
            if d < ALCANCE_GUIZO:
                a.play_spatial("sino", min(0.8, 2.0 / max(d, 1.0)), self._lado(regras.lado_de(s, alvo[0], alvo[1])))
        intervalo = regras.batimento(s)
        self._coracao -= dt
        if intervalo and self._coracao <= 0 and s.pego <= 0 and not s.venceu:
            self._coracao = intervalo
            a.play_one_shot("batida", min(1.0, 0.25 + (9.0 - dist) / 9.0 + (0.25 if s.segurando else 0.0)))

    # ------------------------------------------------------------ desenho
    def render(self, world: World, renderer: IRenderer) -> None:
        agora = time.perf_counter()
        self._fps += ((1 / max(agora - self._ultimo, 1e-6)) - self._fps) * 0.1
        self._ultimo = agora
        s, r = self.estado, self.r3d
        dist = s.dist_vulto()
        perto = max(0.0, 1.0 - s.dist_ameaca() / 8.0)  # a imagem fica mais suja com qualquer um deles perto
        dia = min(1.0, (s.tempo - self._venceu_em) / 4.0) if s.venceu else 0.0  # o amanhecer
        if s.fim == "floresta":
            dia = 0.0  # quem levou o oitavo nao ve o amanhecer
        rosto = s.pego > 0.7 and s.quem_pegou == "vulto"  # os primeiros 1,3 s de "pegou": o rosto dele, de perto
        foto = self._foto_pendente  # o quadro da foto: sem neblina, e com o que a floresta esconde
        vhs = min(1.0, 0.75 * perto ** 1.5 + (0.35 if s.encarando else 0.0) + (0.5 if s.piscando > 0 else 0.0)
                  + 0.12 * s.tensao + (1.0 if rosto else 0.0)) * (1 - dia) * (0.0 if foto else 1.0)
        neb = tuple(c + (t - c) * dia for c, t in zip(self.mapa.nevoa, (0.36, 0.34, 0.40), strict=True))
        noite = regras.escuridao(s)  # a lua se pondo: a neblina fecha
        longe = self.mapa.neblina_longe - 8.0 * noite - 5.0 * s.chuva
        neblina = (3.0, 60.0) if foto else (3.0 + 13 * dia, longe + (45.0 - longe) * dia)
        r.definir_estilo(dataclasses.replace(ESTILO_PS1, grao=0.035 + 0.16 * perto ** 2 * (1 - dia), fundo=neb,
                                             neblina_cor=neb, neblina=neblina, vhs=vhs, espelhar=s.espelho))
        olhos = s.olhos()
        olhar = regras.direcao(s.giro, s.inclina)
        r.definir_camera(olhos, tuple(o + d for o, d in zip(olhos, olhar, strict=True)), 64.0, 0.05, 60.0)
        direita = (math.cos(s.giro), 0.0, math.sin(s.giro))
        origem = (olhos[0] + direita[0] * 0.25, olhos[1] - 0.2, olhos[2] + direita[2] * 0.25)  # na mao direita
        lua = 1.0 - 0.75 * noite
        luzes = [Luz3D("dir", LUA.vetor, tuple(c * lua for c in LUA.cor))]
        forca = regras.forca_da_luz(s)
        if forca > 0:
            luzes.append(Luz3D("foco", origem, (3.9 * forca, 3.6 * forca, 3.1 * forca), 30.0, direcao=s.feixe,
                               cone=(math.cos(math.radians(23)), math.cos(math.radians(9)))))
        if s.sinal > 0 and s.sinal_pos is not None:  # o sinalizador: vermelho, tremendo
            sx, sz = s.sinal_pos
            k = min(1.0, s.sinal / 1.5) * (0.85 + 0.15 * math.sin(s.tempo * 23) * math.sin(s.tempo * 7))
            luzes.append(Luz3D("ponto", (sx, 0.5, sz), (2.6 * k, 0.4 * k, 0.25 * k), 15.0))
        if rosto:
            luzes.append(Luz3D("ponto", olhos, (0.9, 0.75, 0.7), 2.0))
        if s.tempo - self._flash_t < 0.12:  # o flash
            luzes.append(Luz3D("ponto", olhos, (6.0, 6.0, 6.0), 16.0))
        perto_luzes = sorted(self.mapa.luzes, key=lambda luz: math.hypot(luz[0][0] - s.x, luz[0][2] - s.z))
        luzes += [Luz3D("ponto", pos, cor, alc) for pos, cor, alc in perto_luzes[:max(0, 8 - len(luzes))]]
        ceu = tuple(c + (t - c) * dia for c, t in zip((0.06, 0.065, 0.09), (0.55, 0.5, 0.55), strict=True))
        r.definir_iluminacao(Iluminacao3D(ceu=ceu, solo=(0.015 + 0.2 * dia,) * 3, luzes=tuple(luzes)))
        r.atualizar_malha(self.poeira, *self._poeira())
        r.atualizar_malha(self.chuva, *self._chuva())
        r.desenhar(self.cenario)
        self._desenhar_floresta_viva(r)
        if foto:
            self._revelar(r, olhos, olhar)
        if rosto:
            fx, fy, fz = olhar
            tremor = 0.012 * math.sin(s.tempo * 61)
            px, py, pz = olhos[0] + fx * 0.62 + tremor, olhos[1] + fy * 0.62 - 0.02, olhos[2] + fz * 0.62
            r.desenhar(self.m_rosto, translacao_e_giro_y(px, py, pz, math.atan2(olhos[0] - px, olhos[2] - pz)))
        elif not s.venceu and self.mapa.tem_vulto:
            vx, vz = s.vulto
            giro = math.atan2(s.x - vx, s.z - vz)
            r.desenhar(self.vulto, translacao_e_giro_y(vx, 0.0, vz, giro))
            if not s.luz_ligada() and dist < 28.0:  # no escuro, os olhos dele
                r.desenhar(self.m_olhos_vulto, translacao_e_giro_y(vx, 0.0, vz, giro))
        r.desenhar(self.poeira)
        r.desenhar(self.chuva)
        if foto:
            self._revelar_foto(r, renderer)
        self._hud(renderer)

    def _revelar(self, r, olhos, olhar) -> None:
        """So na foto: o que a floresta esconde. Cada foto sorteia onde a crianca esta (perto,
        longe, de um lado ou do outro), e cada noite esconde outra coisa."""
        s, rng = self.estado, self._rng
        fx, fz = olhar[0], olhar[2]
        n = math.hypot(fx, fz) or 1.0
        fx, fz = fx / n, fz / n
        lx, lz = -fz, fx  # para o lado

        def na_frente(dist, lado):
            return olhos[0] + fx * dist + lx * lado, olhos[2] + fz * dist + lz * lado

        def desenhar(malha, x, z, y=None):
            r.desenhar(malha, translacao_e_giro_y(x, self._y(x, z) if y is None else y, z, math.atan2(s.x - x, s.z - z)))

        x0, z0 = self.mapa.jizos[0] if self.mapa.jizos else (0.0, 0.0)
        for k in range(len(s.jizos), 8 if self.mapa.jizos else 0):  # os jizos que ainda nao existem
            desenhar(self.m_jizo, x0 + 1.1 * k, z0, 0.0)
        desenhar(self.m_ayame, *na_frente(rng.uniform(3.5, 7.0), rng.uniform(-1.6, 1.6)))  # a crianca
        if self.mapa.bioma == "arrozal":  # o Cego, parado la no fundo, olhando para a camera
            desenhar(self.m_cego, *na_frente(rng.uniform(11.0, 16.0), rng.uniform(-4.0, 4.0)), -0.2)
        elif self.mapa.bioma == "aldeia":  # uma boneca aos seus pes
            desenhar(self.m_boneca, *na_frente(1.4, rng.uniform(-0.5, 0.5)))

    def _revelar_foto(self, r, renderer: IRenderer) -> None:
        """Guarda o quadro da foto e o carrega como imagem para a polaroide do HUD."""
        self._foto_pendente = False
        px = r.ler_pixels()
        if px is None:
            return
        self._pasta_foto.mkdir(parents=True, exist_ok=True)
        if self.estado.espelho:
            px = px[:, ::-1]
        caminho = self._pasta_foto / f"foto_{self.estado.filme}.ppm"
        h, w, _ = px.shape
        caminho.write_bytes(f"P6 {w} {h} 255\n".encode() + np.ascontiguousarray(px).tobytes())
        renderer.load_texture(ID_FOTO, str(caminho))
        self._foto_t = self.estado.tempo

    def _desenhar_floresta_viva(self, r) -> None:
        s = self.estado
        for i, (ax, az, ay) in enumerate(s.amuletos):  # flutuam e giram devagar
            r.desenhar(self.m_amuleto, translacao_e_giro_y(ax, ay + 0.05 * math.sin(s.tempo * 2 + i), az, s.tempo + i))
        for i, (px, pz) in enumerate(s.pilhas):
            r.desenhar(self.m_pilha, translacao_e_giro_y(px, self._y(px, pz), pz, i * 1.3))
        for i, (tx, tz, fechada) in enumerate(s.armadilhas):
            r.desenhar(self.m_armadilha[int(fechada)], translacao_e_giro_y(tx, self._y(tx, tz) + 0.02, tz, i * 0.7))
        for i, (gx, gz, quebrado) in enumerate(s.gravetos):
            if math.hypot(gx - s.x, gz - s.z) < 30:
                r.desenhar(self.m_graveto[int(quebrado)], translacao_e_giro_y(gx, self._y(gx, gz), gz, i * 2.1))
        for jx, jz, giro in s.jizos:
            r.desenhar(self.m_jizo, translacao_e_giro_y(jx, 0.0, jz, giro))
        for px, pz, _, giro in s.placas:
            r.desenhar(self.m_placa, translacao_e_giro_y(px, 0.0, pz, giro))
        # DESATIVADO (2026-11-12): sinalizador e diario no jogo fora por enquanto -- muita coisa para lembrar
        # for px, pz, _ in s.paginas_no_chao:
            # r.desenhar(self.m_pagina, translacao_e_giro_y(px, self._y(px, pz) + 0.02, pz, px * 1.7))
        if s.ayame is not None:  # correndo para onde ela quer levar voce
            ax, az, tx, tz, _ = s.ayame
            r.desenhar(self.m_ayame, translacao_e_giro_y(ax, self._y(ax, az), az, math.atan2(tx - ax, tz - az)))
        if s.pequena is not None and not (s.pego > 0 and s.quem_pegou == "pequena"):
            qx, qz = s.pequena
            r.desenhar(self.m_pequena, translacao_e_giro_y(qx, self._y(qx, qz), qz, math.atan2(s.x - qx, s.z - qz)))
        estatua = self.m_boneca if self.mapa.estatua == "boneca" else self.m_espantalho
        for ex, ez, eg in s.espantalhos:
            r.desenhar(estatua, translacao_e_giro_y(ex, 0.0, ez, eg))
        for gx, gz, _ in s.sangue:  # o rastro: gotas escuras no chao
            r.desenhar(self.m_gota, translacao_e_giro_y(gx, self._y(gx, gz) + 0.015, gz, gx * 3.1))
        if s.farejador is not None and not (s.pego > 0 and s.quem_pegou == "farejador"):
            fx, fz = s.farejador
            alvo = (s.sangue[0][0], s.sangue[0][1]) if s.sangue else (s.farejo_vaga or (s.x, s.z))
            r.desenhar(self.m_farejador, translacao_e_giro_y(fx, self._y(fx, fz), fz, math.atan2(alvo[0] - fx, alvo[1] - fz)))
        if s.imitadora is not None:  # igual a Ayame -- mas virada para voce, e parada
            ix, iz, _ = s.imitadora
            r.desenhar(self.m_ayame, translacao_e_giro_y(ix, 0.0, iz, math.atan2(s.x - ix, s.z - iz)))
        if s.cego is not None and not (s.pego > 0 and s.quem_pegou == "cego"):
            cx, cz = s.cego
            alvo = s.cego_alvo or (s.x, s.z)
            r.desenhar(self.m_cego, translacao_e_giro_y(cx, -0.2, cz, math.atan2(alvo[0] - cx, alvo[1] - cz)))
        if s.oitavo == "altar":
            ox, oz = self.mapa.altar_oitavo
            r.desenhar(self.m_amuleto, translacao_e_giro_y(ox, 1.0 + 0.05 * math.sin(s.tempo * 2), oz, s.tempo))
        if s.jizo_entrada:
            jx, jz, jg = s.jizo_entrada
            r.desenhar(self.m_jizo, translacao_e_giro_y(jx, self._y(jx, jz), jz, jg))
        if s.arvore_morta is not None:
            r.desenhar(self.m_arvore, translacao_e_giro_y(s.arvore_morta[0], 0.0, s.arvore_morta[1], 0.0))
        for px, pz, giro in s.pegadas:
            r.desenhar(self.m_pegada, translacao_e_giro_y(px, self._y(px, pz) + 0.01, pz, giro))
        if s.sinal > 0 and s.sinal_pos is not None:
            sx, sz = s.sinal_pos
            r.desenhar(self.m_sinal, translacao_e_giro_y(sx, self._y(sx, sz) + 0.02, sz, 0.6))
        if not s.luz_ligada():  # olhos entre as arvores (piscam devagar). Nao sao ele.
            for ox, oy, oz, fase in s.olhos_falsos:
                if math.sin(s.tempo * 0.7 + fase) > -0.6:
                    r.desenhar(self.m_olhos, translacao_e_giro_y(ox, oy, oz, math.atan2(s.x - ox, s.z - oz)))

    def _hud(self, r: IRenderer) -> None:
        s = self.estado
        w, h = r.get_viewport_size()
        r.draw_ui_rect(20, h - 30, 124, 12, (20, 20, 24, 200))
        cor = (220, 210, 150, 230) if s.pilha > 0.25 else (220, 80, 60, 230)
        r.draw_ui_rect(22, h - 28, 120 * s.pilha, 8, cor)
        r.draw_text(152, h - 33, "pilha" + ("" if s.acesa else "  (apagada: recarregando)"), 13, BRANCO)
        if s.segurando or s.ar < 1.0:  # o ar preso
            r.draw_ui_rect(20, h - 48, 124, 8, (20, 20, 24, 200))
            r.draw_ui_rect(22, h - 47, 120 * s.ar, 6, (150, 190, 230, 230) if not s.sem_ar else (200, 90, 80, 230))
            r.draw_text(152, h - 51, "prendendo o ar" if s.segurando else "ar", 12, BRANCO)
        if s.folego > 0.02:  # o folego (a stamina de correr)
            r.draw_ui_rect(20, h - 64, 124, 8, (20, 20, 24, 200))
            cor_folego = (200, 90, 80, 230) if s.sem_folego else (170, 200, 150, 230)
            r.draw_ui_rect(22, h - 63, 120 * (1 - s.folego), 6, cor_folego)
            r.draw_text(152, h - 67, "sem folego" if s.sem_folego else "folego", 12, BRANCO)
        r.draw_text(w - 16, 12, f"{self._fps:4.0f} qps", 13, (120, 120, 120, 255), anchor="topright")
        r.draw_text(20, h - 78, f"omamori: {s.carregando} com voce   {s.depositados} no altar   {len(s.amuletos)} faltando",
                    15, (220, 120, 110, 240))
        # DESATIVADO (2026-11-12): sinalizador e diario no jogo fora por enquanto -- muita coisa para lembrar
        # if s.sinalizadores:
            # r.draw_text(w - 16, h - 33, "sinalizador: G", 13, (220, 110, 90, 220), anchor="topright")
        r.draw_text(w - 16, h - 71, f"camera: {s.filme} fotos (V)", 13, (200, 200, 200, 200), anchor="topright")
        # DESATIVADO (2026-11-12): sinalizador e diario no jogo fora por enquanto -- muita coisa para lembrar
        # r.draw_text(w - 16, h - 90, f"diario: {len(s.paginas)}/{len(mapa.PAGINAS)} paginas (TAB)", 13,
                    # (200, 190, 160, 200), anchor="topright")
        if s.agachado:
            r.draw_text(w - 16, h - 52, "agachado", 13, (170, 170, 170, 220), anchor="topright")
        trapacas = [n for k, n in (("imortal", "nao morre"), ("pilha_infinita", "pilha"), ("filme_infinito", "filme"))
                    if getattr(s, k)]
        if trapacas or s.dev:
            r.draw_text(16, 12, "DEV: " + (", ".join(trapacas) or "F2 radar  F3 ir  F4 x4"), 13, (200, 80, 70, 220))
        if s.dev and self._radar:
            self._desenhar_radar(r, w)
        if s.relogio_noite < 12:  # o comeco de cada noite: os comandos, a historia e a regra desta noite
            alfa = int(255 * min(1.0, (12 - s.relogio_noite) / 2))
            if s.noite_n == 1:
                _centro(r, w / 2, 12, AJUDA, 13, BRANCO[:3] + (alfa,))
                _centro(r, w / 2, 30, AJUDA_2, 13, BRANCO[:3] + (alfa,))
            _centro(r, w / 2, 50, self.mapa.historia, 14, (220, 150, 140, alfa))
            _centro(r, w / 2, 70, REGRA_DA_NOITE.get(self.mapa.bioma, ""), 13, (190, 170, 160, alfa))
        if s.noite_n > 1 and s.relogio_noite < 6:
            alfa = int(255 * min(1.0, (6 - s.relogio_noite) / 2))
            _centro(r, w / 2, h / 2 - 70, NOME_NOITE.get(s.noite_n, f"NOITE {s.noite_n}"), 30, (200, 60, 50, alfa))
            _centro(r, w / 2, h / 2 - 34, self.mapa.nome, 18, (190, 170, 160, alfa))
        texto = regras.bilhete_perto(s) or regras.nome_do_jizo(s) or regras.placa_perto(s)
        if texto and s.pego <= 0:
            self._caixa_de_texto(r, texto, w, h)
        if s.escondido == "submerso":  # embaixo d'agua: escuro, verde, e o ar acabando
            r.draw_ui_rect(0, 0, w, h, (6, 22, 20, 215))
            _centro(r, w / 2, h / 2 + 50, "submerso -- o ar acaba sozinho   (ESPACO sobe)", 15,
                    (170, 210, 200, 230))
        elif s.escondido:
            _centro(r, w / 2, h / 2 + 50, f"escondido {s.escondido} -- ESPACO sai", 15, (190, 190, 200, 230))
            if s.achado:
                _centro(r, w / 2, h / 2 + 72, "ele sabe que voce esta aqui", 15, (230, 80, 70, 255))
        elif s.preso <= 0:
            if s.na_agua == 2 and not s.sem_ar:
                _centro(r, w / 2, h / 2 + 50, "ESPACO: afundar", 15, (170, 210, 200, 230))
            for nome, (ex, ez, *_) in self.mapa.esconderijos.items():
                if math.hypot(s.x - ex, s.z - ez) < regras.ESCONDER:
                    _centro(r, w / 2, h / 2 + 50, f"ESPACO: esconder-se {nome}", 15, (190, 190, 200, 230))
        if s.oitavo == "altar" and not s.venceu:
            _centro(r, w / 2, 14, "No altar ha oito omamori. Voce trouxe sete.", 16, (230, 200, 150, 255))
            _centro(r, w / 2, 38, "ESPACO: deixar o oitavo e esperar o amanhecer   |   ou pegue o oitavo e leve-o de volta",
                    13, (210, 190, 160, 230))
        elif s.oitavo == "levando" and not s.venceu:
            _centro(r, w / 2, 14, "O oitavo esta com voce. O guizo dele toca na direcao da floresta.", 15,
                    (230, 200, 150, 255))
        if s.preso > 0:
            _centro(r, w / 2, h / 2 + 40, "PRESO -- aperte ESPACO para forcar a armadilha", 16, (230, 90, 70, 255))
        elif not s.amuletos and s.carregando and not s.venceu:
            _centro(r, w / 2, 14, "todos os omamori -- leve-os ao santuario", 15, (230, 200, 150, 255))
        if s.venceu and s.fim == "floresta":
            escuro = int(255 * min(1.0, (s.tempo - self._venceu_em) / 3.0))
            r.draw_ui_rect(0, 0, w, h, (0, 0, 0, escuro))
            _centro(r, w / 2, h / 2 - 40, "a floresta ficou com voce", 30, (200, 190, 180, escuro))
            _centro(r, w / 2, h / 2 + 4, "Alguem pequeno segurou a sua mao.", 16, (200, 60, 50, escuro))
            _centro(r, w / 2, h / 2 + 30, f"ESPACO: {self._depois()}", 14, (150, 140, 130, escuro))
        elif s.venceu:
            _centro(r, w / 2, h / 2 - 40, "amanheceu", 34, (40, 34, 30, 255))
            _centro(r, w / 2, h / 2 + 4, "Voce deixou o oitavo no altar.", 16, (60, 30, 28, 255))
            _centro(r, w / 2, h / 2 + 30, f"{s.relogio_noite:.0f} s   |   ESPACO: {self._depois()}", 14,
                    (50, 44, 40, 255))
        if s.sangrando > 0:  # sangrando: as bordas da tela vermelhas, pulsando
            k = 0.5 + 0.5 * math.sin(s.tempo * 5.0)
            for borda in ((0, 0, w, 14), (0, h - 14, w, 14), (0, 0, 14, h), (w - 14, 0, 14, h)):
                r.draw_ui_rect(*borda, (120, 0, 0, int(90 + 70 * k)))
            _centro(r, w / 2, h - 110, "sangrando", 14, (220, 70, 60, 230))
        if 0 < s.pego <= 0.7 or (s.pego > 0 and s.quem_pegou in ("pequena", "cego", "farejador")):
            r.draw_ui_rect(0, 0, w, h, (60, 0, 0, int(220 * min(1.0, (2.0 - s.pego) / 0.6 + 0.3))))
            frase = {"pequena": "ela te achou", "cego": "ele te ouviu", "imitadora": "nao era ela",
                     "farejador": "ele seguiu o rastro"}.get(s.quem_pegou, "ele te achou")
            _centro(r, w / 2, h / 2 - 12, frase, 28, BRANCO)
        if s.tempo - self._foto_t < 5.0:  # a polaroide
            r.draw_ui_rect(w - 300, h - 300, 272, 186, (226, 222, 210, 245))
            r.draw_ui_image(ID_FOTO, w - 292, h - 292, anchor=(0.0, 0.0), scale=0.8)
        flash = s.tempo - self._flash_t
        if 0 <= flash < 0.5:
            r.draw_ui_rect(0, 0, w, h, (255, 255, 255, int(255 * (1 - flash / 0.5))))
        # DESATIVADO (2026-11-12): sinalizador e diario no jogo fora por enquanto -- muita coisa para lembrar
        # if self._diario:
            # self._desenhar_diario(r, w, h)

    def _desenhar_diario(self, r: IRenderer, w: float, h: float) -> None:
        """O diario aberto (TAB): as paginas achadas. A do mapa desenha o mapa -- e ele mente."""
        s = self.estado
        r.draw_ui_rect(0, 0, w, h, (0, 0, 0, 150))
        x0, y0, pw, ph = w / 2 - 300, h / 2 - 210, 600, 420
        r.draw_ui_rect(x0, y0, pw, ph, (214, 204, 182, 250))
        for k in range(1, 14):  # as linhas do caderno
            r.draw_ui_line(x0 + 16, y0 + 30 * k + 20, x0 + pw - 16, y0 + 30 * k + 20, (150, 160, 190, 90))
        r.draw_ui_line(x0 + 50, y0, x0 + 50, y0 + ph, (190, 70, 70, 150))
        if not s.paginas:
            _centro(r, w / 2, h / 2 - 20, "voce ainda nao achou nenhuma pagina", 18, TINTA)
        else:
            i = s.paginas[self._pagina_vista % len(s.paginas)]
            titulo, texto = mapa.PAGINAS[i]
            r.draw_text(x0 + 64, y0 + 18, titulo, 24, TINTA)
            r.draw_text(x0 + pw - 20, y0 + 22, f"{self._pagina_vista % len(s.paginas) + 1}/{len(s.paginas)}", 14,
                        (90, 80, 90, 255), anchor="topright")
            mapa_pagina = i == mapa.PAGINA_MAPA
            if mapa_pagina:
                self._mapa_do_diario(r, x0 + 64, y0 + 60, 300)
            for k, ln in enumerate(_quebrar(texto, 20 if mapa_pagina else 58)):
                r.draw_text(x0 + (384 if mapa_pagina else 64), y0 + 64 + 30 * k, ln, 15 if mapa_pagina else 17, TINTA)
        _centro(r, w / 2, y0 + ph - 30, "W/S troca de pagina   TAB fecha   (lendo, voce para. ele nao.)", 13,
                (90, 70, 70, 255))

    def _mapa_do_diario(self, r: IRenderer, x0: float, y0: float, lado: float) -> None:
        s = self.estado
        k = lado / 80.0

        def p(x, z):
            return x0 + (x + 40) * k, y0 + (z + 40) * k

        for trilha in mapa.TRILHAS:
            for a, b in zip(trilha, trilha[1:], strict=False):
                r.draw_ui_line(*p(*a), *p(*b), (70, 60, 70, 255), 2)
        lugares = dict(mapa.MARCOS)
        if s.mapa_trocado:  # a mentira: dois lugares trocados
            a, b = s.mapa_trocado
            lugares[a], lugares[b] = lugares[b], lugares[a]
        for nome, (x, z) in lugares.items():
            px, pz = p(x, z)
            r.draw_ui_circle(px, pz, 4, (70, 60, 70, 255), 2)
            r.draw_text(px + 6, pz - 7, mapa.NOME_MARCO[nome].split(" ", 1)[1], 11, TINTA)
        sx, sz = p(*mapa.SANTUARIO)
        r.draw_ui_circle(sx, sz, 5, (170, 40, 40, 255))
        r.draw_text(sx + 7, sz - 7, "santuario", 11, (150, 30, 30, 255))

    def _depois(self) -> str:
        return "a noite seguinte" if self.modo == "campanha" else "voltar ao menu"

    @staticmethod
    def _caixa_de_texto(r: IRenderer, texto: str, w: float, h: float) -> None:
        linhas, linha = [], ""
        for palavra in texto.split():  # quebra em linhas de ~70 letras
            if len(linha) + len(palavra) > 70:
                linhas.append(linha)
                linha = ""
            linha = f"{linha} {palavra}".strip()
        linhas.append(linha)
        alto = 22 * len(linhas) + 16
        y0 = h - 110 - alto
        r.draw_ui_rect(w / 2 - 330, y0, 660, alto, (12, 10, 10, 200))
        for i, ln in enumerate(linhas):
            _centro(r, w / 2, y0 + 8 + 22 * i, ln, 15, (226, 214, 190, 255))
