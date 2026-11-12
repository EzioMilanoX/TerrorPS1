# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Composicao: o CompositionRoot monta o renderer "gl" (config.json); o jogo abre no menu, e
cada noite e uma cena empilhada por cima dele (ESC volta)."""
from __future__ import annotations

from ouroboros.bootstrap.composition_root import CompositionRoot
from ouroboros.bootstrap.engine_config import EngineConfig
from ouroboros.bootstrap.game_loop import GameLoop

from terror_ps1.cena import TerrorScene
from terror_ps1.menu import MenuScene


def build_game(config: EngineConfig) -> GameLoop:
    game_loop = CompositionRoot(config).build()

    def jogar(estado, modo: str) -> None:
        game_loop.push_scene(TerrorScene(game_loop.input_provider, game_loop.renderer, game_loop.audio_engine,
                                         ao_sair=game_loop.pop_scene, estado=estado, modo=modo))

    game_loop.reset_scenes(MenuScene(game_loop.input_provider, game_loop.renderer, game_loop.audio_engine,
                                     jogar=jogar, ao_sair=game_loop.stop))
    return game_loop
