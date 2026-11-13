# A história do Terror PS1

Bíblia da história, decidida com o Enzo em 2026-11-12. O código segue isto; mudou aqui, mude o
jogo (verdades, diário, bilhetes).

Inspirado (sem copiar) em três lendas japonesas:
- **Shichinin Misaki**: sete mortos que andam juntos. Um só descansa quando leva alguém, que
  toma o lugar dele; por isso são sempre sete.
- **Kagome Kagome**: a roda em que quem está no meio, de olhos fechados, tem que adivinhar
  quem está atrás.
- **Sai no Kawara**: a margem do rio onde as crianças mortas empilham pedras, e o Jizo as protege.

## O que aconteceu

Você é o irmão (ou irmã; o texto nunca diz) mais velho da **Ayame**. Naquela tarde, a mãe
confiou ela a você. Vocês brincaram de esconde-esconde na floresta. Você contou até dez,
encostado no torii, de olhos fechados, e procurou. Escureceu, você teve medo, **foi para casa e
não contou para ninguém**. Ela ficou escondida a noite toda, esperando você achar.

O **8º omamori** era dela: ela te deu "para você me achar depois". Você volta para devolver.

## Os sete

A aldeia virou os Shichinin Misaki. Cada monstro é alguém que falhou com a Ayame. As 4 primeiras
verdades (morrer para ele) contam a falha dele; **a 5ª mostra que a sua foi igual**.

| Noite | Lugar | Monstro | A falha dele | A sua |
|---|---|---|---|---|
| 1 | floresta | Vulto (só ele) | é você, criança, ainda contando | você parou de procurar |
| 2 | arrozal | Cego | o guarda ouviu ela chamar e não foi | você também ouviu, da janela |
| 3 | aldeia | Imitadora | a vizinha fechou a janela para o choro | você fingiu que dormia |
| 4 | bambuzal | Farejador | o cortador sumiu com o rastro | você sabia onde ela estava |
| 5 | cemitério | Fantoche | a mãe, morta de luto | a coisa nas costas é você |
| 6 | escola | Pequena | sumiu antes; ninguém procurou | quanto tempo você procurou? |
| 7 | o torii | Kagome: a roda | o fim da brincadeira | o sétimo lugar é seu |

Um monstro, uma regra (ver CLAUDE.md). A roda não soma habilidades: é a prova de que você
aprendeu as regras. Os seis te cercam cantando, você fecha os olhos (tela escura) e, quando a
música para, um deles está atrás: pelo som você diz quem é e usa a regra dele. Na última volta
há um lugar vazio na roda.

## Os finais

- **Final falso**: terminar as 7 noites tendo **levado** o 8º omamori em alguma delas. Amanhece,
  você sai. Última imagem: você no torii, de olhos fechados, contando. Tomou o lugar do vulto;
  a corrente continua com sete.
- **Final verdadeiro**: **deixar** o 8º omamori em todas as 7 noites abre a **8ª noite,
  Sai no Kawara**, a margem do rio. Sem monstro. A Ayame está lá, empilhando pedras, ainda
  escondida. Você acha ("achei você"), devolve o omamori, e a contagem acaba.
- Morrer conta o que aconteceu (`verdades.py`): é o caminho da história, não só castigo.

## Depois do fim: o pesadelo

Modo difícil, aberto depois do final: as mesmas noites **espelhadas**, o cenário **pegando
fogo** e **dois monstros por noite**, em pares que se completam (o Enzo escolheu os que se completam: fugir de um é se entregar ao
outro). Os pares e o porquê estão em `mapa.PARES` / `mapa.PARES_TEXTO`; na roda, menos tempo.

## Etapas

1. História: esta bíblia, verdades, diário; a floresta só com o vulto; guardar se o 8º foi
   levado em alguma noite da campanha. **(feito, v0.9)**
2. Noite 6: a escola e a Pequena (ela vem para a luz). **(feito, v0.9)**
3. Noite 7: a roda (Kagome) e o final falso. **(feito, v0.9)**
4. Noite 8: Sai no Kawara e o final verdadeiro. **(feito, v0.9)**
5. O pesadelo (espelhado, fogo, pares). **(feito, v0.9)**
