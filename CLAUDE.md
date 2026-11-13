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
  na noite: F2 radar (com os omamori que faltam e a distância do mais perto), F3 ir para o próximo lugar, F4 acelerar x4 (`cena._ferramentas_dev`). Não documentar o código
  no README (é segredo de dev).

## O cemitério, a morte que conta e a noite sem saída (v0.8, 2026-11-12)
Inspirado (sem copiar) na Chimera do mod Hypno's Lullaby.
- Noite 5 = `cemiterio.py`: túmulos em fileiras (`Mapa.pedras` = x, z, altura), **sem esconderijos**.
  Depois dele, a floresta espelhada (noite 6).
- O Fantoche (`_fantoche`): **uma regra**, só cai com a luz na coisa nas costas
  (`costas_do_fantoche`, e você atrás dela); de frente, nada. Fora isso ela sempre vem
  (`FANTOCHE_VEL`), virando devagar (`FANTOCHE_GIRO`; virada mais que `FANTOCHE_PARA`, só gira).
  Dorme até o 1º omamori (`fantoche_acordou`). Caída: `FANTOCHE_CAIDA` s.
- Agarrado (`_agarrado`, só ela agarra): segurar agachar `AGARRADO_SEGURAR` s, depois
  `AGARRADO_CHUTES` apertos de correr antes de `AGARRADO_TEMPO`; soltou = ela cai. A trapaça
  `imortal` faz soltar.
- A morte conta: `verdades.py` (5 frases por monstro); `progresso.morreu(quem)` guarda a conta.
  A tela de pego dura `regras.PEGO_DURA` (3 s). Na 5ª do Fantoche, ela cai na sua frente.
- Sem saída: quando ela acorda na campanha, `progresso.trancar(noite)`; ESC não sai (dev sai) e
  `composition.build_game` abre direto na noite trancada. `_concluiu` destranca.

## A história (v0.9, 2026-11-12)
- **`HISTORIA.md` é a bíblia**: 7 noites + 1 secreta (Sai no Kawara), monstros = os sete da aldeia
  (Shichinin Misaki), roda Kagome na 7ª, final falso / verdadeiro, o modo pesadelo e as etapas.
  Texto novo (verdades, diário, bilhetes) segue ela.
- A floresta é só do vulto (`Mapa.tem_pequena` agora é `False` por padrão).
- Noite 6 = `escola.py`: um prédio com paredes de verdade (`PAREDES` viram `caixas` e blocos; o
  terreo tem teto em `ALTO`), pátio, ginásio, piscina, coelheira. A Pequena aparece no 1º omamori
  (`Mapa.pequena_aparece`) e **vem para a luz** (`_pequena`): lanterna acesa = ela vem devagar
  (`PEQUENA_INTERVALO_LONGE`), luz nela = correndo; apagada, para. Passa pelas paredes.
  `test_a_escola_tem_tudo_alcancavel_pelas_portas` anda pela colisão e confere tudo alcançável.
- Noite 7 = `torii.py` + `regras._roda`: sem omamori; no meio da clareira (`Mapa.roda_centro`)
  a roda fecha. Estados `Estado.roda`: canto (olhos fechados, parado, lanterna apaga, `RODA_CANTO`)
  → atras (`roda_quem` atrás de você, só som `SOM_NA_RODA`; resposta pela regra dele em
  `RODA_JANELA`) → acertou (ele aparece na sua frente, luz acesa) → ... → vazio (ninguém atrás)
  → fim (`oitavo = "altar"`). Errar/demorar = `_pegar(quem)`; `imortal` conta como acerto.
  Ordem sorteada (`e.rng`). Final: `cena._hud_final` (falso se `_levou`, senão o rio).
- Noite secreta = `rio.py` + `regras._esconde` (`Mapa.tem_esconde`): sem monstro; a Ayame num dos
  `esconde_lugares`, cantarolando (`ESCONDE_CANTA`, som "roda"); luz nela de mais longe que
  `ESCONDE_PERTO` = ela corre para outro lugar. Perto (`ACHAR`), ESPACO = `fim == "achou"`.
- O caminho: depois do torii, `cena` chama `proxima_noite(s, secreta=not _levou)`; continuar a
  campanha usa `regras.noite_da_campanha(c)` (noite 8 + nunca levou = rio). Levou: noite 8 = a
  floresta espelhada (o pesadelo, ainda por fazer). Achou: `progresso.marcar_fim("verdadeiro")` e
  a campanha é apagada; o torii com o oitavo levado marca "falso" (`progresso.fins()`).
- Menu dev: um item "noite" (A/D troca, a última é a secreta) no lugar de uma linha por noite.
- O pesadelo = as noites espelhadas (noite > 7): `mapa.pesadelo(m)` liga o par de `mapa.PARES`
  (monstros que se completam), `Mapa.fogo`/`fogos` (chamas emissivas + luz laranja em cada uma,
  `mapa.geometria_fogo`; o fogo só bloqueia, não fere) e névoa vermelha; na roda, `RODA_PESADELO`.
  O menu mostra "Pesadelo" depois de um final (`progresso.fins()`); começa na noite 8 com
  `levou_oitavo=True` (no pesadelo o rio não abre).
- `progresso.campanha()["levou_oitavo"]`: levou o 8º em alguma noite da campanha (fecha o final
  verdadeiro). Gravado em `cena._concluiu`.

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
O botão "riscar um fósforo" queima o caderno (a chama sobe pela tela, `.fogo-tela`) e troca as
páginas pelo caderno queimado = o pesadelo (`paginas_queimadas()`: uma folha por noite, com o par
de `mapa.PARES_TEXTO` e os números do código; `[[palavra]]` = palavra comida pelo fogo; beiras e
furos sorteados com semente fixa). "o caderno de antes" volta.

## Próximos passos
- Calibrar (só quando o Enzo pedir): raios de som, tensão, frequência das mentiras.
- Ideias que ficaram de fora da v0.2: ser pego custa um amuleto (em vez de recomeçar) e o
  lampião da cabana como lugar seguro que se apaga.
