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

## v0.2 (2026-11-12): o vulto que ouve e a floresta que mente
- Diretor de tensão (`_diretor`): caça ↔ recuo; a noite começa num recuo curto.
- Ele só sabe onde você está pela luz acesa (30 m), por barulho (`_ouviu` com o raio de
  cada som) ou de perto (4,5 m). Sem pista, procura; sem pista por 25 s, a floresta conta.
- Aprende com quem gira a lanterna (`vigilancia`): de perto, só anda quando você está
  vulnerável. O diretor faz a luz falhar (`piscando`) quando você o encara de perto.
- Mentiras (`_mentir`): só depois do 1º amuleto e só fora da vista (`Estado.na_vista`).
  Jizos se viram sempre; o 7º e o 8º aparecem com 3 e 5 amuletos; no recuo, uma mentira
  por vez em rodízio: pegadas, placa, árvore das fitas.
- Fita VHS: `Estilo3D.vhs` da engine (precisa da engine com esse campo).
- O `draw_text` da engine só ancora em topleft/center/topright: use `_centro` para centrar.

## v0.3 (2026-11-12)
- ESPAÇO ("soltar") é a tecla de usar, por contexto (`_usar`): armadilha > sair do
  esconderijo > deixar o oitavo > entrar no esconderijo.
- Esconderijos (`mapa.ESCONDERIJOS`, olhos espiando por fora): escondido não anda; ele só
  acha pela luz acesa, pela respiração a 2,5 m ou se soube de você há < 3 s (viu entrar).
- Câmera: o quadro da foto é desenhado sem neblina e com o que a floresta esconde
  (`_revelar`), lido por `IRenderer3D.ler_pixels` e carregado como textura (PPM).
- Ayame (só no recuo) e a pequena (só anda NA luz, depois do 5º omamori).
- A noite: `relogio_noite`, `escuridao()`, chuva numa janela sorteada (abafa `_ouviu`).
- O oitavo: ao depositar o 7º aparece no altar; deixar (ESPAÇO) = amanhecer; levar (pegar e
  sair 12 m) = a floresta. Depois de um final, `proxima_noite`: espelhada
  (`Estilo3D.espelhar` + comandos e pan invertidos na cena), jizo na entrada, ele lembra
  (`memoria`, `aprendeu_base`). `reiniciar` mantém o que é da noite seguinte (`PERSISTE`).
- Páginas do diário no jogo: `mapa.PAGINAS` (TAB, W/S; lendo, você para). A do mapa mente
  (`mapa_trocado`, a 4ª mentira do rodízio).

## Biomas e noites (v0.4, 2026-11-12)
- Cada noite tem um `Mapa` com os próprios dados (`inicio`, `santuario`, `marcos`, `trilhas`,
  `esconderijos` (x, z, olhos, "seco"/"agua"), `altar_oitavo`, `agua(x, z)`, `nevoa`, e quais
  monstros: `tem_vulto`, `tem_pequena`, `tem_cego`). **As regras leem `e.mapa.*`, nunca as
  constantes de `mapa.py`** (que são só a floresta). `mapa.gerar(bioma)` escolhe o gerador.
- Noite 1 floresta (`mapa.py`), noite 2 arrozais (`arrozal.py`), noite 3 aldeia (`aldeia.py`); `regras.FASES` e
  `bioma_da_noite(n)`: depois da última, recomeça espelhado. Mapa novo = módulo novo com
  `gerar_mapa()` e `geometria()`, entrada em `mapa.gerar`, em `FASES` e em `cena._trocar_de_mapa`.
- O Cego (`_cego`): anda sempre, ignora luz; `_ouviu` também o avisa (raio × `CEGO_OUVIDO`);
  sem som, vaga derivando 1/3 para o jogador (`CEGO_DERIVA`). Água: `VEL_AGUA`, `RUIDO_AGUA`;
  na água funda ESPAÇO afunda (`escondido == "submerso"`, ar no dobro da pressa).
- A Imitadora (`_imitadora`, aldeia): aparece parada à frente (10–16 m), chora; se você não está
  virado para ela (`de_frente`, só o ângulo) e ela está a < 12 m, corre; escondido, ela some.
  `Mapa.estatua` escolhe o que se vira (espantalho/boneca).
- O Farejador (`_farejador`, bambuzal): **uma regra só**, segue `sangue` (gotas em ordem, lambendo
  a mais velha); sem gotas, vaga. O sangue vem de `_cortar` (tocos `Mapa.tocos` de pé, ou
  armadilha nesta noite) e pinga em `_sangrar` (`SANGRA`, `GOTA_CADA`, `SANGUE_SECA`).
- **Um monstro, uma regra**: o Enzo quer cada monstro com poucas mecânicas. Mecânica nova =
  monstro novo (ou noite nova), não mais uma coisa no mesmo monstro.
- Fôlego = stamina: com o fôlego cheio, `sem_folego` (não corre até cair abaixo de `FOLEGO_VOLTA`).
  Submerso: `AR_SUBMERSO` (15 s).
- A distância do monstro mais perto é `dist_ameaca()` (coração, silêncio, sujeira da imagem).

## Menu, campanha e modo desenvolvedor (v0.6, 2026-11-12)
- `menu.py` (`MenuScene`) é a cena base; cada noite (`TerrorScene`) é empilhada por cima e
  sai com `liberar()` + `pop_scene` (ESC). `TerrorScene(estado=, modo=)`: "campanha" (a noite
  seguinte vem depois e o progresso é salvo em `_concluiu`) ou "livre" (no fim volta ao menu).
- `progresso.py`: `%APPDATA%/TerrorPS1/progresso.json` (campanha: noite, `aprendeu_base`,
  `memoria`; noites concluídas). `TERROR_PS1_PROGRESSO` aponta outro arquivo (testes).
  `regras.estado_da_noite(n, ...)` monta o começo de qualquer noite.
- **Código do modo desenvolvedor** = o mesmo do Hertz & Beats: ↑ ↑ ↓ ↓ ← → ← → (setas ou
  WASD), no menu; liga/desliga, só na sessão. Libera: escolher a noite (e espelhada) e as
  trapaças `imortal`, `pilha_infinita`, `filme_infinito` (campos do `Estado`, em `PERSISTE`).
  Todo "pego" passa por `regras._pegar` (onde o "não morrer" atua). Com o modo dev ligado,
  na noite: F2 radar, F3 ir para o próximo lugar, F4 acelerar x4 (`cena._ferramentas_dev`). Não documentar o código
  no README (é segredo de dev).

## Desativados por enquanto (2026-11-12)
O sinalizador e o diário dentro do jogo (as páginas + TAB) saíram: muita coisa para lembrar.
O código continua, comentado, marcado com `DESATIVADO (2026-11-12)` (`grep -rn DESATIVADO`).
Para voltar: descomente esses trechos, volte `sinalizadores` para 1, devolva em
`data/controles.json` as teclas `"sinalizador": ["KEY_G", "MOUSE_MIDDLE"]` e
`"diario": "KEY_TAB"`, e tire o `skip` dos dois testes. No diário em HTML, a página "A luz
vermelha" também está comentada no gerador.

## O diário (docs/diario.html)
Guia do jogo escrito como o diário de quem sobreviveu, com recados em tinta UV (`UV` no gerador,
aparecem com a "luz negra"). Gerado por `tools/gerar_diario.py`:
números, bilhetes, nomes, mapa e controles vêm do código; só a voz do diário mora no
gerador. Mudou regra, texto ou controle? Rode o gerador (`tests/test_diario.py` falha se
esquecer). Ação nova em `controles.json` precisa de frase em `ACAO`.

## Próximos passos
- Calibrar (só quando o Enzo pedir): raios de som, tensão, frequência das mentiras.
- Ideias que ficaram de fora da v0.2: ser pego custa um amuleto (em vez de recomeçar) e o
  lampião da cabana como lugar seguro que se apaga.
