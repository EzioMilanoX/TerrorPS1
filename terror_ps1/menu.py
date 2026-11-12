# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""O menu de entrada: a campanha (continuar ou comecar de novo) e sair.

Escondido: o mesmo codigo dos outros jogos (Hertz & Beats): cima, cima, baixo, baixo,
esquerda, direita, esquerda, direita -- setas ou WASD. Liga e desliga o modo desenvolvedor
(so ate fechar o jogo): escolher qualquer noite, espelhada ou nao, e as trapacas -- nao
morrer, pilha infinita, filme infinito."""
from __future__ import annotations

import math
import tempfile
from collections.abc import Callable
from pathlib import Path

from ouroboros.bootstrap.scene import IScene
from ouroboros.core.world import World
from ouroboros.interfaces.audio_engine import IAudioEngine
from ouroboros.interfaces.input_provider import IInputProvider
from ouroboros.interfaces.renderer import IRenderer

from terror_ps1 import progresso, regras, sons

# cada passo aceita qualquer uma das acoes: as setas viram (girar_*), A/D andam de lado -- as duas valem
_CIMA, _BAIXO, _ESQ, _DIR = ("frente",), ("tras",), ("girar_esq", "esquerda"), ("girar_dir", "direita")
CODIGO = (_CIMA, _CIMA, _BAIXO, _BAIXO, _ESQ, _DIR, _ESQ, _DIR)
ACOES_DO_CODIGO = sorted({a for passo in CODIGO for a in passo})
NOME_BIOMA = {"floresta": "a floresta", "arrozal": "os arrozais", "aldeia": "a aldeia vazia", "bambuzal": "o bambuzal"}
NOME_NOITE = {1: "primeira noite", 2: "segunda noite", 3: "terceira noite", 4: "quarta noite", 5: "quinta noite",
              6: "sexta noite", 7: "setima noite", 8: "oitava noite"}
TRAPACAS = (("imortal", "nao morrer"), ("pilha_infinita", "pilha infinita"), ("filme_infinito", "filme infinito"))
TINTA, APAGADO, SANGUE = (226, 214, 190, 255), (120, 112, 104, 255), (200, 60, 50, 255)


class Codigo:
    """O codigo secreto, como no Hertz & Beats: uma tecla errada zera o progresso -- a nao
    ser que ela mesma ja seja o primeiro passo, e ai recomeca dali."""

    def __init__(self, sequencia=CODIGO) -> None:
        self.sequencia = tuple(sequencia)
        self.progresso = 0

    def apertou(self, acoes: set[str]) -> bool:
        """`acoes`: as acoes apertadas neste quadro. True no aperto que fecha a sequencia."""
        if not acoes:
            return False
        if acoes & set(self.sequencia[self.progresso]):
            self.progresso += 1
            if self.progresso == len(self.sequencia):
                self.progresso = 0
                return True
        else:
            self.progresso = 1 if acoes & set(self.sequencia[0]) else 0
        return False


def nome_da_noite(n: int) -> str:
    bioma, espelho = regras.bioma_da_noite(n)
    return f"{NOME_NOITE.get(n, f'noite {n}')}: {NOME_BIOMA[bioma]}" + (" (espelhada)" if espelho else "")


def itens(dev: bool, campanha: dict | None) -> list[str]:
    """As linhas do menu, em ordem (ids; o texto sai de `texto_do_item`)."""
    lista = (["continuar"] if campanha else []) + ["nova", "sair"]
    if dev:
        lista += [f"noite:{i + 1}" for i in range(len(regras.FASES))] + ["espelhado"] + [k for k, _ in TRAPACAS]
    return lista


class MenuScene(IScene):
    def __init__(self, entrada: IInputProvider, renderer: IRenderer, audio: IAudioEngine | None,
                 jogar: Callable[[regras.Estado, str], None], ao_sair: Callable[[], None]) -> None:
        self.entrada, self.renderer, self.audio = entrada, renderer, audio
        self.jogar, self.ao_sair = jogar, ao_sair
        self.dev = False
        self.espelhado = False
        self.trapacas = {k: False for k, _ in TRAPACAS}
        self.sel = 0
        self.confirmar_nova = False
        self.codigo = Codigo()
        self.tempo = 0.0
        if audio is not None:  # os sons ja ficam prontos (a primeira vez, sao sintetizados aqui)
            for nome, caminho in sons.gerar(Path(tempfile.gettempdir()) / "terror_ps1_sons").items():
                audio.load_sound(nome, str(caminho))

    def on_enter(self, world: World, renderer: IRenderer) -> None:
        self.entrada.set_mouse_captured(False)
        self.confirmar_nova = False

    # ------------------------------------------------------------ logica
    def update(self, world: World, delta_time: float) -> None:
        self.tempo += delta_time
        e = self.entrada
        if e.is_action_pressed("sair"):
            self.ao_sair()
            return
        apertadas = {a for a in ACOES_DO_CODIGO if e.is_action_pressed(a)}
        if self.codigo.apertou(apertadas):  # liga e desliga, como nos outros jogos
            self.dev = not self.dev
            self.sel = 0
            if self.audio is not None:
                self.audio.play_one_shot("sino" if self.dev else "clique", 0.8)
        lista = itens(self.dev, progresso.campanha())
        passo = int(e.is_action_pressed("tras")) - int(e.is_action_pressed("frente"))
        if passo:
            self.sel = (self.sel + passo) % len(lista)
            self.confirmar_nova = False
        self.sel %= len(lista)
        if e.is_action_pressed("soltar"):
            self._escolher(lista[self.sel])

    def _escolher(self, item: str) -> None:
        campanha = progresso.campanha()
        if item == "sair":
            self.ao_sair()
        elif item == "continuar" and campanha:
            self._comecar(regras.estado_da_noite(campanha["noite_n"], campanha.get("aprendeu_base", 0.0),
                                                 campanha.get("memoria", {})), "campanha")
        elif item == "nova":
            if campanha and not self.confirmar_nova:  # apagar o progresso pede um segundo aperto
                self.confirmar_nova = True
                return
            progresso.salvar_campanha(1, 0.0, {})
            self._comecar(regras.estado_da_noite(1), "campanha")
        elif item.startswith("noite:"):
            n = int(item.split(":")[1]) + (len(regras.FASES) if self.espelhado else 0)
            self._comecar(regras.estado_da_noite(n), "livre")
        elif item == "espelhado":
            self.espelhado = not self.espelhado
        elif item in self.trapacas:
            self.trapacas[item] = not self.trapacas[item]

    def _comecar(self, estado: regras.Estado, modo: str) -> None:
        for k, ligada in self.trapacas.items():
            setattr(estado, k, ligada and self.dev)
        estado.dev = self.dev
        self.confirmar_nova = False
        self.jogar(estado, modo)

    # ------------------------------------------------------------ desenho
    def texto_do_item(self, item: str) -> str:
        campanha = progresso.campanha()
        if item == "continuar" and campanha:
            return f"Continuar -- {nome_da_noite(campanha['noite_n'])}"
        if item == "nova":
            return "Nova campanha -- apagar o progresso? (ESPACO de novo)" if self.confirmar_nova else "Nova campanha"
        if item == "sair":
            return "Sair"
        if item.startswith("noite:"):
            i = int(item.split(":")[1])
            n = i + (len(regras.FASES) if self.espelhado else 0)
            bioma, espelho = regras.bioma_da_noite(n)
            feita = (bioma + (" espelhado" if espelho else "")) in progresso.concluidas()
            return f"Noite {i}: {NOME_BIOMA[bioma]}" + (" (espelhada)" if espelho else "") + ("   - concluida" if feita else "")
        if item == "espelhado":
            return f"Espelhado: {'sim' if self.espelhado else 'nao'}"
        nome = dict(TRAPACAS)[item]
        return f"{nome[0].upper()}{nome[1:]}: {'sim' if self.trapacas[item] else 'nao'}"

    def render(self, world: World, renderer: IRenderer) -> None:
        r = renderer
        w, h = r.get_viewport_size()
        r.draw_ui_rect(0, 0, w, h, (8, 8, 11, 255))
        _torii(r, w / 2, 70, (70, 16, 14, 255))
        tremor = 0.85 + 0.15 * math.sin(self.tempo * 9.0) * math.sin(self.tempo * 2.3)  # a luz falhando
        _centro(r, w / 2, 96, "TERROR PS1", 44, (int(210 * tremor), int(196 * tremor), int(180 * tremor), 255))
        _centro(r, w / 2, 148, "Ayame sumiu na floresta. Sete omamori, um santuario, e ate amanhecer.", 14, APAGADO)
        lista = itens(self.dev, progresso.campanha())
        y, passo = (190, 24) if self.dev else (200, 28)
        for i, item in enumerate(lista):
            if item == "noite:1":
                y += 8
                _centro(r, w / 2, y, "MODO DESENVOLVEDOR", 13, SANGUE)
                y += 22
            escolhido = i == self.sel
            cor = TINTA if escolhido else APAGADO
            texto = self.texto_do_item(item)
            _centro(r, w / 2, y, f"> {texto} <" if escolhido else texto, 17 if escolhido else 16, cor)
            y += passo
        _centro(r, w / 2, h - 34, "W/S escolhe   ESPACO confirma   ESC sai", 13, APAGADO)


def _centro(r: IRenderer, x: float, y: float, texto: str, tam: int, cor) -> None:
    r.draw_text(x, y + tam * 0.6, texto, tam, cor, anchor="center")


def _torii(r: IRenderer, x: float, y: float, cor) -> None:
    """Um torii simples ao fundo do titulo."""
    r.draw_ui_rect(x - 150, y - 4, 300, 14, cor)
    r.draw_ui_rect(x - 120, y + 22, 240, 9, cor)
    r.draw_ui_rect(x - 100, y - 4, 12, 150, cor)
    r.draw_ui_rect(x + 88, y - 4, 12, 150, cor)
