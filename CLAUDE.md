# CLAUDE.md — Terror PS1

Guia para o Claude Code neste projeto. Idioma: PT-BR.

## O que é
Terror em primeira pessoa numa floresta low poly estilo PS1. Promovido do blueprint
`SEN-04` (L.A.N.T.E.R.N.); nasceu como `games/terror_ps1` dentro da OuroborosEngine (demo
do M21) e saiu para repo próprio na v0.1.0 (2026-11-11).

## Stack
- OuroborosEngine como repo irmão (`-e ../OuroborosEngine`), renderer `"gl"` (ModernGL,
  `IRenderer3D`). Mudança de comportamento compartilhado (render 3D, entrada, som) começa
  na engine, não aqui.
- `malhas.py` é cópia dos construtores da vitrine (`games/vitrine_estilos/tres_d.py`). Se
  os construtores de malha forem para a engine (próximo passo do M21 no ROADMAP), troque.
- Rodar: `python -m terror_ps1`. Testes: `pytest`. Lint: `ruff check .`.
- Executável: `python -m PyInstaller terror_ps1.spec` (onedir; o onefile é barrado pelo
  Controle Inteligente de Aplicativos).

## Regras de design
- O vulto anda só no escuro (fora do feixe); o som é a pista justa (galho do lado dele).
- Névoa mais clara que os troncos: a mata tem que ler em camadas, nunca virar parede.
- Calibrar só quando o Enzo pedir.

## Próximos passos (do blueprint)
- Memória que mente (SEN-03 M.I.R.A.G.E.): o mapa muda onde você não está olhando.
- Perseguidor que ouve (GAM-09 S.H.A.D.O.W.): passos correndo fazem barulho.
