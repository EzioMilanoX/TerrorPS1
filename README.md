# Terror PS1

Terror em primeira pessoa numa floresta low poly com cara de PlayStation 1. Ache os 7 amuletos e leve-os ao santuário do torii, ao norte, antes que o vulto chegue até você.

- O vulto **só anda quando não está na luz** da lanterna.
- A pilha acaba. Apagada, a lanterna recarrega devagar, e há pilhas pelo mapa.
- Armadilhas de urso nas trilhas prendem você e fazem barulho, e **ele ouve**.
- O guizo do amuleto mais perto toca do lado em que ele está.

## Jogar

Baixe o `TerrorPS1-windows.zip` da página de [Releases](https://github.com/EzioMilanoX/TerrorPS1/releases), extraia e abra `TerrorPS1/TerrorPS1.exe`. Precisa de uma placa de vídeo com OpenGL 3.3 (qualquer integrada recente serve).

| Tecla | Ação |
|---|---|
| Mouse | olhar |
| WASD (Q/E ou setas giram) | andar |
| F ou botão direito | lanterna |
| Espaço ou botão esquerdo | forçar a armadilha / recomeçar |
| F11 | tela cheia |
| Esc | sair |

## Rodar do código

```bash
pip install -r requirements.txt   # a OuroborosEngine como repo irmão (../OuroborosEngine)
python -m terror_ps1               # ou: run.bat
```

## Desenvolvimento

```bash
pytest                                   # testes (regras e mapa, sem placa de vídeo)
ruff check .                             # lint
python -m PyInstaller terror_ps1.spec    # executável em dist/TerrorPS1/
```

## Estrutura

```
terror_ps1/
  regras.py      lanterna, pilha, vulto, armadilhas, itens (lógica pura, testada)
  mapa.py        a floresta 80x80 gerada por semente, marcos, trilhas e colisão
  malhas.py      construtores low poly (bloco, cone, torii...) e o vulto
  cena.py        a cena: render 3D (IRenderer3D da engine), HUD e som
  sons.py        os sons, sintetizados na primeira vez
  data/          config, controles e ícone
tests/
```

Feito na [OuroborosEngine](https://github.com/EzioMilanoX/OuroborosEngine) (render 3D na placa de vídeo, M21). Licença: MPL 2.0.
