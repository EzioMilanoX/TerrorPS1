# Changelog — Terror PS1

## 0.4.0 (2026-11-26)

### Mudou
- **Malhas da engine.** `terror_ps1/malhas.py` deixou de ser a cópia dos construtores da vitrine:
  `bloco`, `cone`, `esfera` (o antigo `icosaedro`), `plano`/`terreno` (o antigo `chao`) e o giro
  (`Malha.girada`, no lugar de `ang`/`pivo`) vêm de `ouroboros.interfaces.malhas3d`. Ficaram no
  jogo os modelos compostos (torii, lanterna, pinheiro, vulto). As `geometria()` e `malha_*`
  devolvem `Malha` em vez de lista de triângulos. Geometria conferida triângulo a triângulo contra
  a versão anterior: igual em tudo, menos o barco virado do arrozal (mesmos vértices; antes era
  um espelho que deixava as faces viradas para dentro, agora é um giro de 90° e as faces ficam
  para fora — a luz bate nele do lado certo).
- **Colisão da engine.** `regras.colidir` e `Mapa.circulos_perto`/`montar_grade` saíram: o mapa
  monta um `MundoColisao3D` (`Mapa.montar_colisao`, `Mapa.mundo`), troncos e postes como
  `Capsula`, paredes como `AABB`, e o jogador anda com `mover_capsula` (`regras.mover`; e
  `regras.assentar`/`regras.livre`). O movimento é dividido em passos curtos (não atravessa
  parede fina), e ser empurrado pelo Fantoche ao soltar agora desliza até lá em vez de
  teletransportar (não atravessa mais parede).
- **Árvores e paredes tapam a visão** (`tem_visao`): a floresta só considera "na vista" o que
  não está atrás de um tronco ou parede (então ela também mente atrás deles), e o vulto só vê a
  sua lanterna de longe (e você entrando no esconderijo) se nada estiver no meio. Obstáculos
  baixos (pedra, mesa, poço, túmulo, carteira, borda da piscina) seguram o corpo mas não tapam.
  Nenhum número de jogo foi recalibrado; na floresta, uma linha de 20 m entre ele e você fica
  tapada cerca de metade das vezes.

### Depende de
- OuroborosEngine com `ouroboros.core.colisao3d` e `ouroboros.interfaces.malhas3d` (engine
  0.4.0 ou mais nova).

## 0.3.0 (2026-11-12)

Publicada como v0.9.0 e renumerada em 2026-11-25 para seguir a sequência (a v0.7.0 virou v0.2.0).
Sete noites, a roda, o rio secreto e o pesadelo (ver `CLAUDE.md` e `HISTORIA.md`).
