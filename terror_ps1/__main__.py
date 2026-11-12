# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Demo de terror PS1 em primeira pessoa, na placa de video (ROADMAP M21; blueprint SEN-04).

Uma floresta de 80x80 com sete marcos: ache os 7 amuletos e leve-os ao santuario do torii,
ao norte. O vulto so anda quando nao esta iluminado; as armadilhas de urso nas trilhas
prendem e fazem barulho, e ele ouve.

    pip install -r requirements.txt
    python -m terror_ps1

Mouse olha, WASD anda (Q/E ou setas tambem giram), F ou botao direito liga/apaga a
lanterna, ESPACO (ou botao esquerdo) forca a armadilha, F11 tela cheia, ESC sai.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

from ouroboros.bootstrap.engine_config import EngineConfig

from terror_ps1.composition import build_game

DADOS = Path(__file__).resolve().parent / "data"  # relativo ao modulo: abre de qualquer pasta, ate no .exe


def carregar_config() -> EngineConfig:
    """O config.json com os caminhos de dados absolutos."""
    cfg = EngineConfig.from_json(str(DADOS / "config.json"))
    return dataclasses.replace(cfg, difficulty_path=str(DADOS / cfg.difficulty_path),
                               input_bindings_path=str(DADOS / cfg.input_bindings_path))


def main() -> int:
    try:  # o icone da janela e da barra de tarefas
        import pygame

        pygame.display.set_icon(pygame.image.load(str(DADOS / "icone.png")))
    except Exception:  # noqa: BLE001 -- sem icone o jogo roda igual
        pass
    game_loop = build_game(carregar_config())
    try:
        game_loop.run()
    finally:
        game_loop.renderer.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
