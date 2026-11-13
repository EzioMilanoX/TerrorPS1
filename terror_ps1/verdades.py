# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""A morte conta a historia: cada vez que um deles te pega, a tela mostra um pouco mais da
verdade sobre ele. A conta de mortes fica salva (`progresso.morreu`); a quinta e a ultima."""
from __future__ import annotations

VERDADES: dict[str, tuple[str, ...]] = {
    "vulto": (
        "ele nao quer voce. quer quem contou ate dez.",
        "ele conta ate dez antes de cada salto.",
        "ele procura. mas so ate escurecer.",
        "ele veste a sua roupa de quando voce era pequeno.",
        "o vulto e voce, no torii, de olhos fechados. voce foi para casa. ele ficou contando.",
    ),
    "pequena": (
        "ela so anda na luz porque tem medo do escuro.",
        "ela sumiu antes da Ayame. ninguem veio procurar.",
        "ela procura a lanterna de alguem.",
        "ela chama todo mundo de irmao.",
        "ninguem procurou por ela. e voce, quanto tempo procurou a Ayame?",
    ),
    "cego": (
        "ele nao nasceu sem olhos.",
        "ele era o guarda dos arrozais.",
        "ele ouviu a Ayame chamar. e nao foi.",
        "ele furou os proprios olhos para nao ver o que nao fez.",
        "voce tambem ouviu ela chamar, da janela. e puxou o cobertor.",
    ),
    "imitadora": (
        "ela aprendeu o choro da Ayame.",
        "ela ouviu a Ayame chorar por tres noites.",
        "ela fechou a janela para conseguir dormir.",
        "ela so imita quem ja morreu.",
        "quando a mae perguntou da Ayame, voce fingiu que dormia.",
    ),
    "farejador": (
        "ele nao tem fome.",
        "ele limpa o caminho para ninguem achar.",
        "ele achou a sandalia dela na trilha. e jogou no rio.",
        "o cortador sumiu. ele apareceu.",
        "voce sabia onde ela tinha se escondido. e nunca disse.",
    ),
    "fantoche": (
        "ela nao anda. e andada.",
        "o quimono e de luto. o enterro era da Ayame. sem corpo.",
        "naquela tarde, ela deixou a Ayame com voce.",
        "a coisa nas costas tem o seu tamanho, de quando voce tinha dez anos.",
        "ela ja estava morta. a coisa nas costas e voce.",
    ),
}
ULTIMA = 5  # na quinta morte, a verdade inteira


def verdade(quem: str, mortes: int) -> str:
    """A frase da `mortes`-esima vez que `quem` te pegou (depois da quinta, sempre a quinta)."""
    frases = VERDADES.get(quem)
    if not frases or mortes < 1:
        return ""
    return frases[min(mortes, len(frases)) - 1]
