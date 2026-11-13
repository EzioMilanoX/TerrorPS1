# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Gera docs/diario.html -- o guia do jogo escrito como o diario de quem sobreviveu a
floresta:  python tools/gerar_diario.py

Os numeros (pilha, raios de som, tempos), os bilhetes, os nomes dos jizos, o mapa e os
controles saem do codigo e dos dados; so a voz do diario e escrita aqui. Cada pagina tem
tambem recados em tinta ultravioleta (`UV`), que so aparecem com o botao "luz negra".

Segredos: no escuro ("apagar a luz") ha frases que mudam (`_dia_noite`), escrita a lapis que
so aparece sem luz (`ESCURO`), olhos fora do alcance da lanterna e vultos quando ela falha --
e quem apaga e acende a luz cinco vezes depressa ve ele inteiro. Na luz negra: maos pequenas,
a contagem dos jizos na margem e uma pagina arrancada que nao esta no indice. Mudou uma regra?
Rode de novo -- `tests/test_diario.py` falha se o diario ficar para tras.
"""
from __future__ import annotations

import html
import json
import math
import random
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from terror_ps1 import aldeia, arrozal, bambuzal, escola, mapa, regras, torii  # noqa: E402
from terror_ps1.cena import ALCANCE_GUIZO, INTERVALO_SINO  # noqa: E402

DESTINO = RAIZ / "docs" / "diario.html"
CONTROLES = RAIZ / "terror_ps1" / "data" / "controles.json"


def n(x: float, casas: int = 1) -> str:
    """Numero a la brasileira: 1,6 -- e sem ',0' a toa."""
    t = f"{x:.{casas}f}"
    if "." in t:  # so corta zeros depois da virgula (30 continua 30)
        t = t.rstrip("0").rstrip(".")
    return t.replace(".", ",")


def b(x: float, unidade: str = "") -> str:
    return f"<b>{n(x)}{unidade}</b>"


# ------------------------------------------------------------------ os controles (de controles.json)

TECLA = {"KEY_LEFT SHIFT": "Shift", "KEY_LEFT CTRL": "Ctrl", "KEY_SPACE": "Espaço", "KEY_ESCAPE": "Esc",
         "KEY_UP": "↑", "KEY_DOWN": "↓", "KEY_LEFT": "←", "KEY_RIGHT": "→", "MOUSE_LEFT": "botão esquerdo",
         "MOUSE_RIGHT": "botão direito", "MOUSE_MIDDLE": "botão do meio"}
ACAO = {"frente": "ir em frente", "tras": "voltar de costas", "esquerda": "passo para a esquerda",
        "direita": "passo para a direita", "girar_esq": "virar para a esquerda", "girar_dir": "virar para a direita",
        "correr": "correr (cansa, e faz barulho)", "agachar": "agachar, segurando", "prender_ar": "prender o ar, segurando",
        "lanterna": "acender e apagar a lanterna", "foto": "tirar uma foto (o flash)",
        "sinalizador": "acender o sinalizador", "diario": "abrir o diário (as páginas que achei)",
        "soltar": "usar: forçar a armadilha, entrar e sair do esconderijo, deixar o oitavo",
        "tela_cheia": "tela cheia", "sair": "desistir (sair)"}


def _tecla(codigo: str) -> str:
    return TECLA.get(codigo, codigo.removeprefix("KEY_"))


def controles() -> list[tuple[str, str]]:
    dados = json.loads(CONTROLES.read_text(encoding="utf-8"))
    faltando = {a for a in dados if not a.startswith("dev_")} - set(ACAO)  # as teclas de dev ficam fora
    if faltando:
        raise SystemExit(f"o diario nao sabe descrever: {sorted(faltando)} (ponha em ACAO)")
    linhas = [("mouse", "olhar em volta")]
    for acao, frase in ACAO.items():
        if acao in dados and not acao.startswith("dev_"):
            teclas = dados[acao] if isinstance(dados[acao], list) else [dados[acao]]
            linhas.append((" ou ".join(_tecla(t) for t in teclas), frase))
    return linhas


# ------------------------------------------------------------------ os esbocos (SVG a lapis)

def _px(x: float, z: float) -> tuple[float, float]:
    """Mundo (-40..40) para o papel (0..400). O norte (santuario, -z) fica em cima."""
    return (x + 40) * 5, (z + 40) * 5


def _tremido(pontos, rng: random.Random, passo: float = 2.0, amplitude: float = 0.35) -> str:
    """Uma linha a mao: subdivide e treme um pouco."""
    out = []
    for (ax, az), (bx, bz) in zip(pontos, pontos[1:], strict=False):
        k = max(1, int(math.hypot(bx - ax, bz - az) / passo))
        for i in range(k):
            t = i / k
            out.append((ax + (bx - ax) * t + rng.uniform(-amplitude, amplitude),
                        az + (bz - az) * t + rng.uniform(-amplitude, amplitude)))
    out.append(pontos[-1])
    return " ".join(f"{_px(x, z)[0]:.1f},{_px(x, z)[1]:.1f}" for x, z in out)


def esboco_mapa(m: mapa.Mapa) -> str:
    rng = random.Random(4)
    partes = ['<svg class="esboco mapa" viewBox="0 0 400 400" role="img" '
              'aria-label="Mapa da floresta desenhado a mao: trilhas, os sete lugares, o santuario ao norte">']
    partes.append('<rect x="8" y="8" width="384" height="384" class="borda"/>')
    for trilha in mapa.TRILHAS:
        partes.append(f'<polyline points="{_tremido(trilha, rng)}" class="trilha"/>')
    for i, (x, z) in enumerate(m.armadilhas):
        if i % 2 == 0:  # so as que eu achei
            px, pz = _px(x, z)
            partes.append(f'<path d="M{px - 3:.1f},{pz - 3:.1f} l6,6 m0,-6 l-6,6" class="x"/>')
    for nome, (x, z) in mapa.MARCOS.items():
        px, pz = _px(x, z)
        rotulo = html.escape(mapa.NOME_MARCO[nome].removeprefix("a ").removeprefix("o ").removeprefix("os "))
        partes.append(f'<circle cx="{px:.1f}" cy="{pz:.1f}" r="5" class="marco"/>')
        dx = -8 if x > 10 else 9
        ancora = "end" if x > 10 else "start"
        partes.append(f'<text x="{px + dx:.1f}" y="{pz + 4:.1f}" text-anchor="{ancora}">{rotulo}</text>')
    ax, az = _px(*mapa.ARVORE_MORTA_OUTRA)
    partes.append(f'<text x="{ax:.1f}" y="{az + 4:.1f}" class="duvida" text-anchor="middle">?</text>')
    partes.append(f'<text x="{ax:.1f}" y="{az + 20:.1f}" class="nota-svg" text-anchor="middle">(a árvore, às vezes?)</text>')
    sx, sz = _px(*mapa.SANTUARIO)
    partes.append(f'<path d="M{sx - 12:.1f},{sz - 6:.1f} h24 M{sx - 9:.1f},{sz - 2:.1f} h18 '
                  f'M{sx - 7:.1f},{sz - 6:.1f} v16 M{sx + 7:.1f},{sz - 6:.1f} v16" class="torii"/>')
    partes.append(f'<text x="{sx:.1f}" y="{sz - 12:.1f}" text-anchor="middle" class="destaque">santuário</text>')
    ix, iz = _px(*mapa.INICIO)
    partes.append(f'<text x="{ix:.1f}" y="{iz + 18:.1f}" text-anchor="middle">entrei aqui</text>')
    partes.append(f'<path d="M{ix:.1f},{iz + 4:.1f} v-8 m-3,3 l3,-3 l3,3" class="trilha"/>')
    partes.append('<text x="380" y="34" text-anchor="end" class="nota-svg">N ↑</text>')
    px, pz = _px(*mapa.MARCOS["poco"])
    partes.append(f'<text x="{px - 6:.1f}" y="{pz + 26:.1f}" text-anchor="end" class="uv-svg">ela tá aqui embaixo ↑</text>')
    partes.append('<text x="18" y="384" class="nota-svg">x = armadilha</text>')
    partes.append("</svg>")
    return "".join(partes)


def esboco_ruido() -> str:
    """Os raios do que ele ouve, em escala."""
    escala = 140 / max(regras.RUIDO_PASSO["correndo"], regras.RUIDO_GRAVETO, regras.RUIDO_ARFAR)
    # (nome, raio, lado do rotulo, altura do rotulo, angulo no anel) -- rotulos nas bordas, com um risco ate o anel
    aneis = [("correndo", regras.RUIDO_PASSO["correndo"], 1, 26, -55), ("graveto", regras.RUIDO_GRAVETO, -1, 26, -125),
             ("arfar", regras.RUIDO_ARFAR, 1, 300, 50), ("andando", regras.RUIDO_PASSO["andando"], -1, 300, 130),
             ("ele sente", regras.SENTE, 1, 168, 0), ("agachado", regras.RUIDO_PASSO["agachado"], -1, 168, 180)]
    cx, cy = 230, 164
    partes = ['<svg class="esboco ruido" viewBox="0 0 460 330" role="img" '
              'aria-label="Circulos de ate onde ele ouve cada barulho">']
    for nome, raio, lado, ty, ang in aneis:
        r = raio * escala
        partes.append(f'<circle cx="{cx}" cy="{cy}" r="{r:.1f}" class="anel{" tracejado" if nome == "ele sente" else ""}"/>')
        px, py = cx + r * math.cos(math.radians(ang)), cy + r * math.sin(math.radians(ang))
        tx = 452 if lado > 0 else 8
        partes.append(f'<path d="M{px:.1f},{py:.1f} L{tx - lado * 74:.1f},{ty - 5}" class="risco"/>')
        partes.append(f'<text x="{tx}" y="{ty}" text-anchor="{"end" if lado > 0 else "start"}" class="nota-svg">'
                      f"{nome} {n(raio)} m</text>")
    partes.append(f'<circle cx="{cx}" cy="{cy}" r="3" class="eu"/></svg>')
    return "".join(partes)


ESBOCO_VULTO = (
    '<svg class="esboco vulto" viewBox="0 0 170 300" role="img" aria-label="Esboco dele: alto, magro, bracos longos, '
    'cabeca caida para o lado">'
    '<path d="M60,74 q-4,10 -2,22" class="traco"/>'
    '<ellipse cx="54" cy="52" rx="13" ry="22" transform="rotate(-22 54 52)" class="traco"/>'
    '<path d="M47,50 l3,1 M57,46 l3,1 M51,64 q3,3 6,0" class="traco fino"/>'
    '<path d="M42,96 q18,-6 36,0 l-6,90 q-12,4 -24,0 z" class="traco"/>'
    '<path d="M42,98 q-10,60 -8,118 m2,0 l-4,14 m6,-14 l0,15 m4,-15 l4,13" class="traco"/>'
    '<path d="M78,98 q10,60 8,118 m-2,0 l-4,14 m6,-14 l0,15 m4,-15 l4,13" class="traco"/>'
    '<path d="M52,186 l-4,104 M68,186 l4,104" class="traco"/>'
    '<text x="92" y="30" class="nota-svg">mais alto</text><text x="92" y="46" class="nota-svg">que a porta</text>'
    '</svg>')


def _dia_noite(de_dia: str, de_noite: str) -> str:
    """Uma frase com duas versoes: a da luz e a que se le no escuro (com a lanterna)."""
    return f'<span class="dia">{de_dia}</span><span class="noite">{de_noite}</span>'


def esboco_jizos() -> str:
    partes = ['<svg class="esboco jizos" viewBox="0 0 400 130" role="img" aria-label="A fileira de jizos: seis, depois '
              'sete, depois oito">']
    for i in range(8):
        x = 30 + i * 47
        classe = "traco" if i < 6 else "traco tracejado"
        partes.append(f'<path d="M{x - 13},90 v-30 q13,-10 26,0 v30 z" class="{classe}"/>'
                      f'<circle cx="{x}" cy="46" r="10" class="{classe}"/>'
                      f'<path d="M{x - 11},62 q11,10 22,0" class="tinta-vermelha"/>')
        nome = html.escape(mapa.NOMES_JIZO[i] if i < 6 else ("?" if i == 6 else mapa.NOMES_JIZO[7]))
        partes.append(f'<text x="{x}" y="112" text-anchor="middle" class="{"destaque" if i == 7 else ""}">{nome}</text>')
    partes.append('<text x="300" y="20" class="nota-svg">eram seis.</text>')
    partes.append('<text x="20" y="22" class="uv-svg">|||| |   |||| ||   |||| |||</text>')  # 6, 7, 8
    partes.append('<text x="20" y="126" class="uv-svg">conta de novo</text></svg>')
    return "".join(partes)


# ------------------------------------------------------------------ as paginas

DESCRICAO = {
    "cabana": "Quatro paredes e um telhado que pinga. Tem um lampião aceso que ninguém acendeu. O diário do "
              "guarda fica na mesa.",
    "poco": "Não olhe para dentro. Não jogue nada dentro. Se jogar, não espere o barulho.",
    "arvore_morta": "Uma árvore seca cheia de fitas de pano amarradas nos galhos. Cada fita é um nome.",
    "pedras": "Oito pedras em pé, em círculo, e um altar baixo no meio. É o lugar mais quieto da floresta.",
    "jizo": "A fileira de estátuas com babadores vermelhos e velas. Conte quantas são toda vez que passar.",
    "troncos": "Dois troncos caídos atravessados. Bom lugar para se agachar.",
    "acampamento": "Uma barraca caída e brasas que ainda estão quentes. Quem estava aqui saiu com pressa.",
}


ONDE_ACHEI = {"cabana": "na mesa da cabana", "poco": "na beira do poço", "arvore_morta": "no pé da árvore das fitas",
              "pedras": "no altar do círculo de pedras", "jizo": "junto das velas dos jizos",
              "troncos": "entre os troncos caídos", "acampamento": "no acampamento"}


def paginas(m: mapa.Mapa) -> list[tuple[str, str, str, str]]:
    """(id, rotulo, titulo, corpo html) de cada pagina."""
    r = regras
    pilha, recarga = 1 / r.GASTO_PILHA, 1 / r.RECARGA_PILHA
    encarando = 1 / (r.GASTO_PILHA + r.GASTO_ENCARAR)
    ctl = "".join(f"<li><span class=\"tecla\">{html.escape(t)}</span> — {html.escape(f)}</li>" for t, f in controles())
    lugares = "".join(f"<li><b>{html.escape(mapa.NOME_MARCO[k])}</b> — {html.escape(DESCRICAO[k])}</li>"
                      for k in mapa.MARCOS)
    bilhetes = [("na placa da entrada", mapa.BILHETE_INICIO)] + [(ONDE_ACHEI[k], t) for k, t in mapa.TEXTOS.items()]
    papeis = "".join(f'<figure class="papel"><blockquote>{html.escape(t)}</blockquote>'
                     f"<figcaption>achado {html.escape(onde)}</figcaption></figure>" for onde, t in bilhetes)
    nomes = "".join(f"<li>{html.escape(nome)}</li>" for nome in mapa.NOMES_JIZO[:6])
    um, dois = r.JIZOS_A_MAIS
    recuo_min, recuo_max = r.RECUO
    cala, volta = r.SILENCIO
    falso_min, falso_max = r.SINO_FALSO
    peso_max = round((1 - 0.6) * 100)
    lista_esconderijos = ", ".join(html.escape(k) for k in mapa.ESCONDERIJOS)
    esconderijos_arrozal = ", ".join(html.escape(k) for k in arrozal.ESCONDERIJOS)
    esconderijos_aldeia = ", ".join(html.escape(k) for k in aldeia.ESCONDERIJOS)
    esconderijos_bambuzal = ", ".join(html.escape(k) for k in bambuzal.ESCONDERIJOS)

    return [
        ("antes", "véspera", "Antes de entrar", f"""
<p>Ayame sumiu há três noites, na floresta ao sul da aldeia. Naquela tarde a mãe deixou ela comigo.
Ninguém quis vir comigo. Vou anotar
tudo, porque se eu não voltar, alguém vai ter que vir depois.</p>
<p>Levo uma lanterna de dínamo, uma câmera descartável e este caderno. O velho da venda disse que
os omamori das crianças ficam onde elas sumiram, e que quem levar os <b>{len(m.amuletos)}</b> ao
santuário antes de amanhecer "acerta a conta". Não perguntei de quê.</p>
<p class="nota">o que o corpo sabe fazer:</p>
<ul class="lista teclas">{ctl}</ul>"""),

        ("lanterna", "noite 1", "A lanterna", f"""
<p>A pilha cheia dura uns {b(pilha, " s")} acesa. Apagada, o dínamo enche tudo de novo em
{b(recarga, " s")}, então eu apago sempre que posso. Mas no escuro eu não vejo nada.</p>
<p>O feixe é estreito: só pega o que está bem no meio, uns {b(math.degrees(r.CONE_VULTO), "°")}
para cada lado, até uns {b(r.ALCANCE_LUZ, " m")}. Abaixo de um quarto de carga, ela começa a
<span class="tremido">piscar</span> sozinha.</p>
<p>Achei <b>{len(m.pilhas)}</b> pilhas soltas na beira das trilhas. Cada uma devolve
<b>{n(r.CARGA_PILHA * 100)}%</b> da carga.</p>
<p class="nota">apontar para ELE gasta muito mais. encarando, a pilha cheia vira uns {n(encarando, 0)} s.</p>"""),

        ("ele", "noite 1", "Ele", f"""
<div class="lado-a-lado"><div>
<p>Alto demais. Magro demais. Os braços passam dos joelhos e a cabeça cai para um lado, como se o
pescoço não aguentasse.</p>
<p><b>Na luz, ele não se mexe.</b> Nem um dedo. Fora da luz, anda aos saltos, e cada salto quebra
um galho: dá para ouvir <i>de que lado</i> ele está.</p>
<p>Cada omamori que eu pego deixa ele mais inquieto: os saltos vêm mais rápido e mais longos.</p>
<p>Se eu me afasto demais (mais de {b(r.LONGE_DEMAIS, " m")}), ele não me segue. Ele aparece
<b>atrás</b> de mim.</p>
<p>No escuro, os olhos dele são os <span class="vermelho">vermelhos</span>. Tem outros olhos entre
as árvores quando eu apago a luz. Esses não se mexem. Não sei o que são.</p>
<p class="nota">a {n(r.PEGOU)} m dele, acabou. vi o rosto uma vez. não vou desenhar o rosto.</p>
</div>{ESBOCO_VULTO}</div>"""),

        ("ouve", "noite 2", "O que ele ouve", f"""
<p>Ele não sabe onde eu estou. Ele <i>descobre</i>. A lanterna acesa ele vê de
{b(r.VE_A_LUZ, " m")}; de {b(r.SENTE, " m")} ele me sente, faça o que eu fizer. O resto é barulho:</p>
<table class="tabela">
<tr><td>correndo</td><td>{n(r.RUIDO_PASSO["correndo"])} m</td></tr>
<tr><td>pisando num graveto</td><td>{n(r.RUIDO_GRAVETO)} m</td></tr>
<tr><td>arfando (não aguentei prender o ar)</td><td>{n(r.RUIDO_ARFAR)} m</td></tr>
<tr><td>andando</td><td>{n(r.RUIDO_PASSO["andando"])} m</td></tr>
<tr><td>ofegando depois de correr</td><td>até {n(r.RUIDO_RESPIRA)} m</td></tr>
<tr><td>os omamori tilintando no bolso</td><td>{n(r.RUIDO_TILINTAR)} m cada (metade agachado)</td></tr>
<tr><td>agachado</td><td>{n(r.RUIDO_PASSO["agachado"])} m</td></tr>
</table>
{esboco_ruido()}
<p>Uma armadilha fechando se ouve de longe: ele corre metade do caminho até mim na hora.</p>
<p class="nota">se eu ficar quieto no escuro por muito tempo (uns {n(r.SEM_PISTA_MAX, 0)} s), a floresta
conta para ele onde eu estou. não dá para só esperar.</p>"""),

        ("respirar", "noite 2", "Respirar", f"""
<p>Correr cansa. Depois de correr eu fico ofegante, e ofegar se ouve de perto. Se eu correr até o
fôlego acabar, não corro mais: só depois de descansar.</p>
<p>Dá para <b>prender o ar</b> por uns {b(r.AR_DURA, " s")}. Se eu não soltar a tempo, o ar sai de
uma vez, alto, e ele escuta de {b(r.RUIDO_ARFAR, " m")}. O fôlego volta em uns {b(r.AR_VOLTA, " s")}.</p>
<p class="nota">ele perto + eu ofegando = agachar, apagar e prender. contar até cinco. soltar devagar.</p>"""),

        ("omamori", "noite 3", "Os omamori", f"""
<p>São <b>{len(m.amuletos)}</b>, um em cada lugar do mapa. Saquinhos vermelhos, flutuando um pouco
acima de onde deviam estar caídos.</p>
<p>O guizo do mais perto toca a cada {b(INTERVALO_SINO, " s")} quando estou a menos de
{b(ALCANCE_GUIZO, " m")}, do lado em que ele está.</p>
<p>Eles pesam. Cada um no bolso me deixa uns {b(r.PESO_AMULETO * 100, "%")} mais lento (no máximo
{peso_max}%), e eles tilintam a cada passo. Dá para deixar os que já tenho no altar do santuário e
voltar mais leve. Com os {len(m.amuletos)} no altar, amanhece.</p>
<p class="nota">nem todo guizo é um omamori. ver "ele aprende".</p>"""),

        ("mapa", "noite 3", "O mapa que eu fiz", f"""
<figure class="com-fita">{esboco_mapa(m)}</figure>
<ul class="lista">{lugares}</ul>
<p>As placas nas bifurcações apontam para os lugares. <span class="riscado">Dá para confiar nelas.</span></p>"""),

        ("papeis", "noite 3", "Os papéis que achei", f"""
<p>Tem papel escrito espalhado pela floresta. Copiei todos aqui, do jeito que estavam.</p>
{papeis}"""),

        ("armadilhas", "noite 4", "Armadilhas e gravetos", f"""
<p>Alguém encheu as trilhas de armadilhas de urso: contei <b>{len(m.armadilhas)}</b>. Sem luz, não
se vê. Ela prende por {b(r.PRESO, " s")}; batendo com força (Espaço), sai antes. Depois eu manco
por uns {b(r.MANCANDO, " s")}.</p>
<p>E tem gravetos secos por todo lado nas trilhas, uns <b>{len(m.gravetos)}</b>. De pé, eles
estalam alto ({n(r.RUIDO_GRAVETO)} m). <b>Agachado, o pé acha o graveto antes de pisar.</b></p>
<p class="nota">o barulho da armadilha acaba com qualquer calma. ele vem.</p>"""),

        ("ritmo", "noite 4", "Ele tem ritmo", f"""
<p>Não é sempre igual. Ele aperta, aperta, chega cada vez mais perto, e quando eu acho que não
aguento mais, ele <b>recua</b>. Fica longe por {n(recuo_min, 0)} a {n(recuo_max, 0)} segundos. A
noite começa assim, num recuo curto.</p>
<p>Os grilos, os sapos e a coruja <b>calam</b> quando ele chega a {b(cala, " m")} de mim, e só
voltam quando ele está a mais de {b(volta, " m")}.</p>
<p class="nota grande">se os grilos param, não importa o que eu vejo. ele está perto.</p>
<p>É no recuo, no silêncio bom, que a floresta muda. Ver "a floresta mente".</p>"""),

        ("aprende", "noite 5", "Ele aprende", f"""
<p>Na segunda noite eu fiquei girando a lanterna em volta de mim o tempo todo. Funcionou por um
tempo. Depois ele <b>parou de vir</b> quando eu estava atento, e começou a esperar: quando eu
apagava, quando eu ficava preso, quando a luz falhava. E aí vinha o dobro.</p>
<p>E a luz falha. Quando eu o encaro de perto, ela pisca justo nessa hora. Não é a pilha.</p>
<p>E ele imita o guizo. De vez em quando (a cada {n(falso_min, 0)} a {n(falso_max, 0)} s, se ele
estiver longe o bastante e fora da minha vista) eu ouço um guizo do lado dele, igual ao
de verdade.</p>
<p class="nota">guizo onde não tem omamori por perto = ele chamando.</p>"""),

        ("mente", "noite 5", "A floresta mente", f"""
<p>Até eu pegar o primeiro omamori, a floresta é honesta. Depois, não. E ela nunca muda nada
<b>enquanto eu estou olhando</b>.</p>
{esboco_jizos()}
<ul class="lista">
<li>Os jizos se viram para mim quando eu não estou olhando.</li>
<li>Eram seis. Com {um} omamori comigo, eram sete. Com {dois}, oito.</li>
<li>A árvore das fitas não estava onde eu deixei. Estava a leste, depois voltou.</li>
<li>Uma placa que apontava para a cabana passou a apontar para outro lugar.</li>
<li>Achei pegadas. As botas são as minhas. Saem da trilha para dentro do mato, para um lado onde
eu nunca fui.</li>
</ul>
<p class="nota">não siga as pegadas.</p>"""),

        ("nomes", "noite 5", "Os nomes", f"""
<p>Os jizos têm nomes escritos na base. Só dá para ler de perto, com a luz.</p>
<ol class="lista nomes">{nomes}</ol>
<p>O sétimo é uma pedra lisa, sem nome. <i>Ainda.</i></p>
<p>O oitavo diz {_dia_noite(f'<b class="vermelho">{html.escape(mapa.NOMES_JIZO[7])}</b>.',
                            '<b class="vermelho">o meu nome</b>.')}</p>"""),

        # DESATIVADO (2026-11-12): sinalizador e diario no jogo fora por enquanto -- muita coisa para lembrar
        # ("sinalizador", "noite 6", "A luz vermelha", f"""
# <p>Um sinalizador só, por noite. Queima por {b(r.SINAL_DURA, " s")}. Dentro de
# {b(r.SINAL_RAIO, " m")} dele, ele não se mexe; se estava perto quando eu acendi, ele recua.</p>
# <p class="nota">não gaste à toa. é a única vez que a floresta fica vermelha e calma ao mesmo tempo.</p>"""),

        ("esconder", "noite 6", "Esconderijos", f"""
<p>Achei três lugares para sumir: {lista_esconderijos}. Entro e saio com a mesma tecla de forçar a
armadilha.</p>
<p>Escondido, eu não ando e não faço barulho de passo. Mas <b>se ele soube de mim nos últimos
{n(r.VIU_ENTRAR, 0)} segundos</b>, ele me viu entrar, e o esconderijo não serve de nada. Lanterna
acesa lá dentro também me entrega.</p>
<p>Uma hora ele vem conferir. Se ele chegar a {b(r.ACHA_ESCONDIDO, " m")} e eu estiver
respirando, ele me acha. <b>Prender o ar</b> é o que me salvou.</p>
<p class="nota">ele lembra. na noite seguinte, o lugar onde eu me escondi não serve mais.</p>"""),

        ("camera", "noite 6", "A câmera", f"""
<p>Uma câmera descartável com <b>{r.FILME}</b> fotos. O flash cega ele por uns
{b(r.FLASH_CONGELA, " s")} se ele estiver na frente, até {b(r.FLASH_ALCANCE, " m")}, num cone de
uns {n(math.degrees(r.FLASH_CONE), 0)}° para cada lado.</p>
<p>Mas o clarão se vê de longe: se ele não estava na frente, agora ele sabe onde eu estou.</p>
<p><b>Na foto aparece o que a floresta esconde.</b> Jizos que ainda não estão lá. Alguém parado na
minha frente, que não estava lá quando eu apertei.</p>
<p class="nota">não olhe as fotos por muito tempo.</p>"""),

        ("ayame", "noite 7", "Ayame", f"""
<p>Vi uma criança correndo entre as árvores. A yukata clara, a faixa vermelha. É ela. Só aparece
quando está tudo calmo, e longe.</p>
<p>Ela não me deixa chegar perto: a uns {b(r.AYAME_SOME, " m")} ela some. Mas ela corre para algum
lugar. Quase sempre ({n(r.AYAME_LEVA_AO_AMULETO * 100, 0)}% das vezes que eu anotei) é um omamori.
As outras vezes é uma armadilha.</p>
<p class="nota">os passinhos dela vêm do lado em que ela está.</p>"""),

        ("noite", "noite 8", "A lua e a chuva", f"""
<p>A noite piora. Em uns {n(r.NOITE / 60, 0)} minutos a lua se põe e a neblina fecha.</p>
<p>No meio da noite (entre {n(r.CHUVA_COMECA[0] / 60, 0)} e {n(r.CHUVA_COMECA[1] / 60, 0)} minutos)
começa a chover, por uns {n(r.CHUVA_DURA[0] / 60, 0)} a {n(r.CHUVA_DURA[1] / 60, 0)} minutos. A
chuva cobre o barulho: tudo o que eu faço chega a {b(r.CHUVA_ABAFA * 100, "%")} da distância.
Mas eu também não ouço o galho dele, e os grilos se calam com a chuva, então o silêncio não avisa
mais nada.</p>
<p class="nota">na chuva eu fico mais escondido e mais cego ao mesmo tempo.</p>"""),

        ("oitavo", "noite 9", "O oitavo", """
<p>Quando o sétimo omamori fica no altar, aparece um oitavo. Ninguém trouxe.</p>
<p>Dá para deixar ele lá e esperar o amanhecer. Ou pegar e levar de volta para a floresta.</p>
<p>Eu deixei.</p>
<p class="nota">não sei o que acontece com quem leva.</p>"""),

        ("arrozais", "segunda noite", "Os arrozais", f"""
<p>Amanheceu, e anoiteceu de novo, em outro lugar: os arrozais da represa, alagados desde a
enchente. Campo aberto, água parada até a canela, diques de terra entre as quadras e um canal fundo
cortando tudo de leste a oeste, com uma ponte só.</p>
<p>Na água rasa eu ando a {b(r.VEL_AGUA[1] * 100, "%")} da velocidade e cada passo espirra
({n(r.RUIDO_AGUA[1])} m; agachado, a metade). No canal, {b(r.VEL_AGUA[2] * 100, "%")} e
{n(r.RUIDO_AGUA[2])} m. <b>Nos diques, o chão é seco e quieto</b> — mas é lá que estão as
armadilhas.</p>
<p>Para sumir: {esconderijos_arrozal}, ou <b>afundar no canal</b> (a tecla de usar, na água funda).
Embaixo d'água ninguém me vê nem me ouve, mas o ar acaba sozinho: uns
{n(r.AR_SUBMERSO, 0)} segundos, e eu subo arfando.</p>
<p class="nota">os espantalhos se viram para mim. como os jizos.</p>"""),

        ("cego", "segunda noite", "O Cego", f"""
<p>O guarda da represa. Enorme, mais de três metros, curvado, a cabeça enrolada em faixas. Não tem
olhos. <b>A luz não muda nada para ele</b>: ele anda com a lanterna na cara.</p>
<p>Mas ele ouve tudo, {n(r.CEGO_OUVIDO * 100 - 100, 0)}% mais longe que o outro: um passo na água
ele ouve de {n(r.RUIDO_AGUA[1] * r.CEGO_OUVIDO)} m; correndo, de {n(r.RUIDO_PASSO["correndo"] * r.CEGO_OUVIDO)} m.
Quando ouve, ele geme e <b>corre</b> para o som. Se não ouve nada, ele vaga devagar, e cada volta
dele termina um pouco mais perto de mim.</p>
<p>Os passos dele são pesados, na água, e vêm do lado em que ele está. O coro de sapos cala quando
ele chega perto.</p>
<p class="nota">se ele esbarrar em mim (uns {n(r.CEGO_PEGA)} m), acabou. ficar parado e quieto
funciona. até ele tropeçar em mim.</p>"""),

        ("aldeia", "terceira noite", "A aldeia vazia", f"""
<p>A aldeia. As casas fechadas, as lanternas de papel ainda acesas na rua principal, ninguém.
A venda do velho, a escola, a torre de vigia, o banho público, o cemitério. E a casa dos Mori,
onde Ayame morava: na parede, um desenho da família. Cinco pessoas. Nós éramos quatro.</p>
<p>Nas varandas, bonecas de madeira. Elas se viram para mim, como os jizos.</p>
<p>Para sumir: {esconderijos_aldeia}.</p>
<p class="nota">não responda a ninguém que chame pelo seu nome.</p>"""),

        ("imitadora", "terceira noite", "A Imitadora", f"""
<p>Vi Ayame no meio da rua, parada, olhando para mim. Chorando. Quase corri até ela.</p>
<p><b>A Ayame de verdade nunca fica parada</b>: ela corre para longe, e dá para ouvir os passinhos.
<b>A outra espera</b>, de frente, e chora. Ela aparece no meu caminho, a uns
{n(r.IMITA_LONGE[0], 0)} ou {n(r.IMITA_LONGE[1], 0)} metros.</p>
<p>Enquanto eu olho para ela, ela não se mexe. Se eu der as costas com ela a menos de
{b(r.IMITA_ALCANCE, " m")}, ela corre. Rápido. Mais rápido que eu.</p>
<p>Ela esquece de quem some: se eu me escondo, quando eu saio ela não está mais lá.</p>
<p class="nota">recuar sem tirar os olhos dela. dar a volta pela outra rua.</p>"""),

        ("bambuzal", "quarta noite", "O bambuzal", f"""
<p>Um bambuzal fechado, com trilhas estreitas. A cabana do cortador, o forno de carvão, uma cabeça
de pedra caída de lado, a clareira das lanternas, o sino.</p>
<p>Fora da trilha, o chão é cheio de <b>tocos de bambu cortados em ponta</b>. De pé, o toco corta a
canela e eu sangro por uns {b(r.SANGRA, " s")}. Agachado, o pé acha o toco antes. A armadilha também
corta.</p>
<p>Para sumir: {esconderijos_bambuzal}.</p>
<p class="nota">não corte caminho pelo bambu.</p>"""),

        ("farejador", "quarta noite", "O Farejador", f"""
<p>Comprido, de quatro, o pescoço esticado e a cabeça rente ao chão. Não tem olhos. Não ouve. Ele
<b>só segue o meu sangue</b>.</p>
<p>Sangrando, eu deixo uma gota a cada {n(r.GOTA_CADA)} m (parado, uma por segundo). Ele segue as
gotas <b>na ordem em que caíram</b>, lambendo uma por uma, mais devagar que eu andando
({n(r.FAREJA_VEL)} m/s) e mais rápido que eu agachado. Gota com mais de {n(r.SANGUE_SECA, 0)} s
seca, e ele não quer.</p>
<p>Quando eu paro de sangrar, ele chega na última gota e se perde. Escondido sem sangrar, ele passa
do lado. Escondido sangrando, o rastro leva até a porta.</p>
<p class="nota">dá para ouvir ele farejando, do lado em que está.</p>"""),

        ("cemiterio", "quinta noite", "O cemitério", """
<p>O cemitério do templo. Fileiras e fileiras de túmulos de pedra, as tábuas de madeira atrás,
o portão velho, o crematório, a casa do zelador, o salgueiro, o poço, o ossuário. E o túmulo dos
Mori: cinco nomes. Um deles ainda sem data.</p>
<p><b>Aqui não tem onde se esconder.</b> Não adiantaria: ela sabe onde eu estou.</p>
<p>Na porta do crematório tinha uma mulher deitada de bruços, de quimono de luto. Quando eu peguei
o primeiro omamori, ela levantou.</p>
<p class="nota">daqui até o amanhecer não há saída. fechar os olhos não adianta. acordar também não.</p>"""),

        ("fantoche", "quinta noite", "O Fantoche", f"""
<p>Ela não anda. <b>É andada.</b> Agarrada nas costas dela tem uma coisa pálida, encolhida, com dedos
compridos por cima dos ombros dela. A coisa é que olha. A coisa é que sabe.</p>
<p>Ela vem sempre na minha direção, a {n(r.FANTOCHE_VEL)} m/s: mais devagar que eu andando, mas
carregando omamori eu fico mais lento que ela. Ela <b>vira devagar</b>. Quando eu fico de lado, ela
para e só gira.</p>
<p>A luz no rosto dela não faz nada: a morta não sente. <b>A luz tem que pegar a coisa, nas costas.</b>
Aí ela cai, e fica uns {b(r.FANTOCHE_CAIDA, " s")} no chão, até a coisa levantar ela de novo.
Quem passa correndo do lado dela fica atrás.</p>
<p>Se ela me agarrar, eu caio. Primeiro <b>segurar abaixado</b>, para ela não me levantar. Depois
<b>chutar, chutar, chutar</b> ({r.AGARRADO_CHUTES} chutes, correr) antes de {b(r.AGARRADO_TEMPO, " s")}.
Quando eu soltei, ela caiu.</p>
<p class="nota">cada vez que um deles me pega, eu lembro de mais uma coisa. na quinta vez, de tudo.</p>"""),

        ("escola", "sexta noite", "A escola", f"""
<p>A escola primária da aldeia. O pátio de terra, o balanço, a coelheira vazia, o ginásio trancado,
a piscina sem água. E o prédio de madeira: o corredor comprido, a sapateira, a enfermaria, as
salas, a sala de música. O relógio da frente parou. Atrás do prédio, o santuário.</p>
<p>Lá dentro é escuro de verdade. A placa de saída, verde, é a única luz que ficou.</p>
<p>Para sumir: {", ".join(html.escape(k) for k in escola.ESCONDERIJOS)}.</p>
<p class="nota">na sala 2-1 falta uma carteira.</p>"""),

        ("pequena", "sexta noite", "A pequena", f"""
<p>Os mais velhos falam de outra criança que sumiu antes da Ayame. Ninguém foi procurar. Ela ainda
está na escola: pequena, de quatro, os braços compridos para a frente. Apareceu quando eu peguei o
primeiro omamori.</p>
<p>Ela tem medo do escuro. <b>Ela vem para a luz.</b> Com a lanterna acesa, ela vem devagar, de onde
estiver, e passa pelas paredes. Se a luz pega nela, ela vem correndo. Apaguei, e ela parou.</p>
<p>Mas no escuro eu também não enxergo nada. Acender, olhar, apagar. Quando ela se mexe, as juntas
estalam: é por ali que ela está.</p>
<p class="nota">a {n(r.PEQUENA_PEGA)} m dela, acabou.</p>"""),

        ("torii", "sétima noite", "O torii", f"""
<p>A clareira. O torii onde eu contei até dez. Em volta, sete pedras pequenas com babador vermelho.
Seis. No lugar da sétima, só terra.</p>
<p>Não tem omamori para achar. Quando eu cheguei no meio, <b>eles fecharam a roda</b>: os seis,
de mãos dadas, girando em volta de mim. Cantando. Eu fechei os olhos.</p>
<p>Quando a música para, um deles está <b>atrás de mim</b>. De olhos fechados, só dá para saber
quem é pelo som. E cada um quer uma coisa:</p>
<ul class="lista">{"".join(f"<li>{html.escape(t)}</li>" for t in torii.TEXTOS)}</ul>
<p>Demorar mais que {b(r.RODA_JANELA, " s")} também é errar.</p>
<p class="nota">na última volta, atrás de mim não tinha ninguém.</p>"""),

        ("pesadelo", "depois", "O pesadelo", f"""
<p>Depois do fim, eu voltei. Tudo de novo, mas <b>ao contrário</b>, e pegando fogo. E agora eles
não vêm sozinhos: cada noite tem dois, e um completa o outro. Fugir de um é se entregar ao outro.</p>
<ul class="lista">{"".join(f"<li>{html.escape(t)}</li>" for t in mapa.PARES_TEXTO.values())}</ul>
<p class="nota">o fogo não queima. só ilumina o que eu não queria ver.</p>"""),

        ("terceira", "depois", "De novo", """
<p>A floresta de novo. Mas <b>ao contrário</b>: a esquerda era a direita.
O meu mapa não servia mais.</p>
<p>Tinha um jizo na entrada. Ele não esperou: não teve calma no começo. Ele já sabia girar a luz
contra mim (ele começa sabendo, no mínimo, o que aprendeu antes). Ele lembrava onde eu tinha me
escondido.</p>
<p class="nota">ele lembra de tudo o que eu fiz.</p>"""),

        ("ultima", "", "", f"""
<div class="outra-letra">
<p>Achei este caderno na mesa da cabana, debaixo do diário do guarda.</p>
<p>A letra é a minha.</p>
<p>Eu não me lembro de ter escrito nada disso.</p>
<p>No altar havia oito omamori. Eu trouxe {_dia_noite("sete", "oito")}.</p>
<p class="depois-de-ver">Ele estava atrás de você.</p>
</div>"""),
    ]


# ------------------------------------------------------------------ o caderno queimado (o pesadelo)

def paginas_queimadas() -> list[tuple[str, str, str, str]]:
    """O que sobra quando o caderno pega fogo (o botao do fosforo): o pesadelo, noite por noite.
    `[[palavra]]` = palavra que o fogo comeu."""
    t, r = mapa.PARES_TEXTO, regras
    return [
        ("q-capa", "", "", """
<h1>Diário</h1>
<p class="sub">o que sobrou</p>
<p class="aviso">o fogo não queima. ele mostra.</p>"""),

        ("q-floresta", "pesadelo · 1", "A floresta pegando fogo", f"""
<p><b>{html.escape(t["floresta"])}</b></p>
<p>Tudo ao contrário: a esquerda era a direita. As árvores queimando dos dois lados da trilha, e o fogo
não [[esquentava]]. Ele estava lá, como sempre. E no {mapa.PESADELO_PEQUENA}º omamori, ela também.</p>
<p>Ele só anda fora da luz. Ela vem para a luz, e com a luz nela vem correndo. Acender, achar ele,
apagar antes que ela chegue. Nunca deixar a luz [[parada]].</p>"""),

        ("q-arrozal", "pesadelo · 2", "Os arrozais em chamas", f"""
<p><b>{html.escape(t["arrozal"])}</b></p>
<p>Os diques queimando, e a água devolvendo o fogo. Ela, a de luto, deitada no fim do campo até eu
pegar o primeiro omamori. Depois ela vem, sempre, a {n(r.FANTOCHE_VEL)} m/s, e só cai com a luz na
coisa nas costas.</p>
<p>Para ficar atrás dela eu tenho que correr em volta. Correndo, ele me ouve de
{b(r.RUIDO_PASSO["correndo"] * r.CEGO_OUVIDO, " m")}. Na água, [[pior]].</p>"""),

        ("q-aldeia", "pesadelo · 3", "A aldeia queimando", f"""
<p><b>{html.escape(t["aldeia"])}</b></p>
<p>As lanternas de papel pegando fogo uma por uma. A falsa parada no meio da rua, chorando. Se eu
desviar o olho com ela perto, ela corre. Então eu olho. E enquanto eu olho para ela, ele anda: atrás
de mim, no [[escuro]], onde a lanterna não está.</p>
<p class="nota">andar de costas. olhar para ela. ouvir o galho.</p>"""),

        ("q-bambuzal", "pesadelo · 4", "A trilha de cinzas", f"""
<p><b>{html.escape(t["bambuzal"])}</b></p>
<p>Os tocos em ponta no chão. Com a luz eu vejo e desvio, mas a luz chama a pequena. No escuro eu
piso, corto, e sangro {b(r.SANGRA, " s")}; o Farejador lambe cada [[gota]], na ordem.</p>"""),

        ("q-cemiterio", "pesadelo · 5", "As duas", f"""
<p><b>{html.escape(t["cemiterio"])}</b></p>
<p>Os túmulos queimando como velas. Para derrubar a de luto eu tenho que ficar atrás dela. E aí eu
dou as costas para a falsa. Uma das duas sempre está [[atrás]] de mim.</p>"""),

        ("q-escola", "pesadelo · 6", "A escola em chamas", f"""
<p><b>{html.escape(t["escola"])}</b></p>
<p>Apagar a luz para a pequena parar. Acender nas costas da de luto para ela cair. Nunca as duas ao
mesmo tempo. O corredor de madeira estala, e eu não sei mais se são as juntas dela ou o [[fogo]].</p>"""),

        ("q-torii", "pesadelo · 7", "A roda, mais depressa", f"""
<p><b>{html.escape(t["torii"])}</b></p>
<p>A mesma música, eles em volta, e o torii queimando. Mas quando a música para eu tenho
{b(r.RODA_JANELA * r.RODA_PESADELO, " s")}, e não {n(r.RODA_JANELA)}.</p>
<p class="nota">o sétimo lugar continua vazio. [[ainda]].</p>"""),

        ("q-ultima", "", "", """
<div class="outra-letra">
<p>Se você está lendo isto, o caderno já pegou fogo uma vez.</p>
<p>A gente nunca parou de brincar.</p>
<p>Conta de novo.</p>
</div>"""),
    ]


def _chamuscar(texto: str) -> str:
    return re.sub(r"\[\[(.+?)\]\]", r'<span class="cinza" aria-label="queimado">\1</span>', texto)


def _borda_queimada(rng: random.Random) -> str:
    """Um clip-path com a beira roida pelo fogo (sorteada, mas sempre a mesma: a semente e fixa)."""
    pts = []
    for k in range(15):
        pts.append((k / 14 * 100, rng.uniform(0, 3.2)))
    for k in range(1, 15):
        pts.append((100 - rng.uniform(0, 2.4), k / 14 * 100))
    for k in range(13, -1, -1):
        pts.append((k / 14 * 100, 100 - rng.uniform(0, 4.0)))
    for k in range(13, 0, -1):
        pts.append((rng.uniform(0, 2.4), k / 14 * 100))
    return "polygon(" + ", ".join(f"{x:.1f}% {y:.1f}%" for x, y in pts) + ")"


def _furos(rng: random.Random) -> str:
    furos = []
    for _ in range(rng.randint(1, 3)):
        lado = rng.choice(("left", "right"))
        furos.append(f'<span class="furo" style="{lado}: {rng.uniform(-3.5, 0.5):.1f}%; '  # mordendo a beira
                     f'top: {rng.uniform(8, 82):.1f}%; width: {rng.randint(34, 64)}px; height: {rng.randint(30, 56)}px">'
                     '</span>')
    return "".join(furos)


def caderno_queimado() -> str:
    rng = random.Random(1945)
    secoes = []
    for pid, rotulo, titulo, conteudo in paginas_queimadas():
        cab = f'<span class="rotulo">{html.escape(rotulo)}</span>\n<h2>{html.escape(titulo)}</h2>' if titulo else ""
        classe = "folha capa" if pid == "q-capa" else "folha ultima" if not titulo else "folha"
        secoes.append(f'<section class="pagina queimada" id="{pid}"><div class="{classe}" '
                      f'style="clip-path: {_borda_queimada(rng)}">{cab}{_chamuscar(conteudo.strip())}'
                      f'{_furos(rng)}</div></section>')
    return "\n".join(secoes)


# ------------------------------------------------------------------ a pagina

CSS = """
:root {
  --mesa: #15120f; --papel: #ece2cc; --papel-2: #e3d6bb; --tinta: #2b2a35; --tinta-suave: #5a5664;
  --linha: rgba(70, 100, 150, .22); --margem: rgba(190, 60, 60, .45); --vermelho: #a3201b;
  --fita: rgba(226, 214, 170, .78); --mancha: rgba(120, 80, 40, .10);
  --uv: #c6ff7a; --uv-halo: rgba(168, 110, 255, .95);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --papel: #2c2822; --papel-2: #26221d; --tinta: #d9cfbb; --tinta-suave: #a59c8b;
    --linha: rgba(150, 170, 210, .12); --margem: rgba(200, 80, 70, .35); --vermelho: #e0574c;
    --fita: rgba(120, 110, 80, .55); --mancha: rgba(0, 0, 0, .25);
  }
}
:root[data-theme="dark"] {
  --papel: #2c2822; --papel-2: #26221d; --tinta: #d9cfbb; --tinta-suave: #a59c8b;
  --linha: rgba(150, 170, 210, .12); --margem: rgba(200, 80, 70, .35); --vermelho: #e0574c;
  --fita: rgba(120, 110, 80, .55); --mancha: rgba(0, 0, 0, .25);
}
* { box-sizing: border-box; }
html { background: var(--mesa); }
body { margin: 0; background: var(--mesa); color: var(--tinta); overflow-x: hidden;
  font: 19px/32px "Kalam", "Segoe Print", "Comic Sans MS", cursive; padding: 40px 16px 120px; }
h1, h2, .nota, .rotulo, figcaption, .outra-letra { font-family: "Caveat", "Segoe Print", cursive; }
.pagina { position: relative; max-width: 780px; margin: 0 auto 56px; padding: 40px 40px 40px 84px;
  background:
    radial-gradient(circle at 88% 12%, var(--mancha) 0 34px, transparent 36px 42px, var(--mancha) 43px 45px, transparent 46px),
    linear-gradient(90deg, transparent 63px, var(--margem) 63px 65px, transparent 65px),
    repeating-linear-gradient(transparent 0 31px, var(--linha) 31px 32px),
    linear-gradient(170deg, var(--papel), var(--papel-2));
  background-position: 0 0, 0 0, 0 8px, 0 0;
  box-shadow: 0 18px 40px rgba(0,0,0,.55), 0 1px 0 rgba(255,255,255,.04) inset; }
.pagina:nth-of-type(odd) { transform: rotate(-.35deg); }
.pagina:nth-of-type(even) { transform: rotate(.3deg); }
.pagina:not(:nth-of-type(3n)) { background-size: 0 0, auto, auto, auto; }
.rotulo { position: absolute; top: 10px; right: 28px; font-size: 22px; color: var(--tinta-suave); }
h1 { font-size: 72px; line-height: 1; margin: 24px 0 8px; letter-spacing: .02em; }
h2 { font-size: 44px; line-height: 64px; margin: 0 0 8px; font-weight: 700; }
p { margin: 0 0 32px; }
b { font-weight: 700; }
a { color: inherit; text-decoration-color: var(--vermelho); text-underline-offset: 4px; }
.nota { color: var(--vermelho); font-size: 27px; transform: rotate(-1.5deg); margin: 0 0 32px 8px; }
.nota.grande { font-size: 34px; line-height: 40px; }
.vermelho { color: var(--vermelho); }
.riscado { text-decoration: line-through 2px var(--vermelho); }
.tremido { display: inline-block; animation: piscar 3.2s infinite steps(1); }
@keyframes piscar { 0%, 70%, 100% { opacity: 1; } 72%, 76% { opacity: .15; } 74% { opacity: .8; } }
.lista { margin: 0 0 32px; padding-left: 1.2em; }
.lista li { margin: 0; }
.teclas { list-style: none; padding: 0; }
.tecla { display: inline-block; min-width: 2.2em; padding: 0 8px; line-height: 26px; text-align: center;
  border: 1.5px solid currentColor; border-radius: 6px 9px 7px 8px; font-size: 16px; margin-right: 4px; }
.tabela { border-collapse: collapse; margin: 0 0 32px; width: 100%; }
.tabela td { border-bottom: 1.5px dashed var(--tinta-suave); padding: 0 6px; line-height: 31px; }
.tabela td:last-child { text-align: right; font-weight: 700; }
.esboco { display: block; width: 100%; height: auto; margin: 0 auto 32px; color: var(--tinta);
  font-family: "Caveat", cursive; font-size: 17px; }
.esboco text { fill: currentColor; }
.esboco .nota-svg { fill: var(--vermelho); font-size: 16px; }
.esboco .destaque { fill: var(--vermelho); font-size: 19px; font-weight: 700; }
.esboco .duvida { fill: var(--vermelho); font-size: 30px; }
.esboco .borda { fill: none; stroke: var(--tinta-suave); stroke-width: 1; stroke-dasharray: 2 5; }
.esboco .trilha, .esboco .traco { fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round;
  stroke-linejoin: round; }
.esboco .fino { stroke-width: 1.2; }
.esboco .tracejado { stroke-dasharray: 4 4; }
.esboco .x, .esboco .tinta-vermelha, .esboco .torii { fill: none; stroke: var(--vermelho); stroke-width: 2; stroke-linecap: round; }
.esboco .marco { fill: var(--papel); stroke: currentColor; stroke-width: 2; }
.esboco .anel { fill: none; stroke: currentColor; stroke-width: 1.4; }
.esboco .risco { fill: none; stroke: var(--vermelho); stroke-width: 1; opacity: .7; }
.esboco .eu { fill: var(--vermelho); }
.mapa { max-width: 520px; }
.ruido { max-width: 560px; }
.jizos { max-width: 560px; }
.lado-a-lado { display: grid; grid-template-columns: 1fr 190px; gap: 24px; align-items: start; }
.vulto { max-width: 190px; }
.com-fita { position: relative; margin: 0 0 32px; }
.com-fita::before, .com-fita::after { content: ""; position: absolute; width: 110px; height: 28px; background: var(--fita);
  top: -10px; box-shadow: 0 1px 2px rgba(0,0,0,.15); }
.com-fita::before { left: 12%; transform: rotate(-6deg); }
.com-fita::after { right: 12%; transform: rotate(5deg); }
.papel { margin: 0 0 32px; padding: 14px 20px 6px; background: rgba(255,255,255,.28); border: 1px solid var(--tinta-suave);
  transform: rotate(var(--giro, -.6deg)); box-shadow: 2px 3px 0 rgba(0,0,0,.08); }
:root[data-theme="dark"] .papel { background: rgba(0,0,0,.18); }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) .papel { background: rgba(0,0,0,.18); } }
.papel:nth-of-type(even) { --giro: .8deg; }
.papel blockquote { margin: 0; font-family: "Special Elite", "Courier New", monospace; font-size: 16px; line-height: 26px; }
.papel figcaption { text-align: right; color: var(--tinta-suave); font-size: 21px; }
.capa { text-align: center; padding-top: 80px; padding-bottom: 80px; }
.capa .sub { font-family: "Caveat", cursive; font-size: 30px; color: var(--tinta-suave); }
.capa .aviso { font-family: "Caveat", cursive; font-size: 26px; color: var(--vermelho); transform: rotate(-3deg); }
.indice { columns: 2; column-gap: 32px; list-style: none; padding: 0; margin: 0 0 32px; counter-reset: pag; }
.indice li { counter-increment: pag; break-inside: avoid; }
.indice li::before { content: counter(pag) ". "; color: var(--tinta-suave); }
.ultima { min-height: 420px; display: flex; align-items: center; }
.outra-letra { font-size: 34px; line-height: 48px; transform: rotate(-2.5deg); color: var(--vermelho);
  letter-spacing: .03em; }
.outra-letra p { margin: 0 0 20px; }
.luz { position: fixed; right: 16px; bottom: 16px; z-index: 20; font: 22px "Caveat", cursive; cursor: pointer;
  background: var(--papel); color: var(--tinta); border: 1.5px solid var(--tinta); border-radius: 10px 14px 9px 12px;
  padding: 6px 16px; box-shadow: 0 6px 18px rgba(0,0,0,.5); }
.topo { position: fixed; left: 16px; bottom: 16px; z-index: 20; font: 22px "Caveat", cursive; color: #d9cfbb;
  text-decoration: none; opacity: .75; }
body.escuro::after { content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 10;
  background: radial-gradient(circle 190px at var(--mx, 50%) var(--my, 45%), transparent 0 55%, rgba(4,4,6,.93) 100%); }
body.escuro.pisca::after { background: rgba(4,4,6,.97); }
body.uv-on::after { content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 10;
  background: radial-gradient(circle 210px at var(--mx, 50%) var(--my, 45%), rgba(120, 50, 255, .16) 0 52%, rgba(9, 3, 22, .95) 100%); }
.uv { position: absolute; z-index: 2; margin: 0; max-width: 62%; color: transparent; pointer-events: none;
  user-select: none; font: 700 30px/34px "Caveat", "Segoe Print", cursive; letter-spacing: .04em; }
.uv-0 { top: 74px; right: 36px; transform: rotate(7deg); }
.uv-1 { bottom: 22px; right: 70px; transform: rotate(-4deg); }
.uv-2 { top: 46%; left: 96px; transform: rotate(-9deg); }
body.uv-on .uv { color: var(--uv); text-shadow: 0 0 6px var(--uv), 0 0 22px var(--uv-halo); }
.esboco .uv-svg { fill: transparent; font-size: 18px; font-weight: 700; }
body.uv-on .esboco .uv-svg { fill: var(--uv); }
.luz.uv-btn { right: auto; left: 50%; transform: translateX(-50%); background: #1d1030; color: #d9c8ff; border-color: #8a5cff; }
/* --- segredos do escuro --- */
.noite { display: none; }
body.escuro .noite { display: inline; }
body.escuro .dia { display: none; }
.depois-de-ver { display: none; }
body.visto .depois-de-ver { display: block; }
.lapis { display: none; margin: 0 0 32px; color: var(--tinta-suave); opacity: .55; font: 24px/32px "Caveat", cursive;
  transform: rotate(-1deg); letter-spacing: .05em; }
body.escuro .lapis { display: block; }
.aparicao { position: fixed; left: 0; top: 0; z-index: 9; width: 110px; height: 275px; pointer-events: none; opacity: 0; }
.aparicao.ve { opacity: .93; }
.aparicao.grande { z-index: 12; width: 42vh; height: 100vh; left: 50% !important; top: 0 !important;
  transform: translateX(-50%); }
.sombra-svg { width: 100%; height: 100%; fill: #050404; }
.sombra-svg .olho-vermelho { fill: #ff3326; }
.clarao { position: fixed; inset: 0; z-index: 11; background: #f4efe6; opacity: 0; pointer-events: none; }
.clarao.ve { opacity: .9; }
.olho-par { position: fixed; z-index: 11; width: 20px; height: 7px; pointer-events: none; opacity: 0;
  transition: opacity .35s; background: radial-gradient(circle at 3px 3px, #ff3a2a 0 2px, transparent 3px),
  radial-gradient(circle at 17px 3px, #ff3a2a 0 2px, transparent 3px); filter: drop-shadow(0 0 3px #ff2a1a); }
body.escuro .olho-par.vivo { opacity: .85; }
/* --- segredos da luz negra --- */
.arrancada { display: none; clip-path: polygon(0 3%, 6% 0, 13% 2.5%, 21% .5%, 30% 3%, 38% 1%, 47% 3.5%, 55% .5%,
  64% 2.5%, 72% 0, 81% 3%, 90% 1%, 100% 2.5%, 100% 100%, 0 100%); }
body.uv-on .arrancada { display: block; }
.uv-texto { color: transparent; font: 700 30px/40px "Caveat", cursive; padding-top: 24px; }
body.uv-on .uv-texto { color: var(--uv); text-shadow: 0 0 6px var(--uv), 0 0 22px var(--uv-halo); }
.uv-mao { position: absolute; left: 22px; bottom: 30px; width: 46px; z-index: 2; pointer-events: none; transform: rotate(-14deg); }
.mao-svg { width: 100%; fill: transparent; }
body.uv-on .mao-svg { fill: var(--uv); filter: drop-shadow(0 0 5px var(--uv)); opacity: .8; }
/* --- o caderno queimado (o fosforo): o pesadelo --- */
.queimada { display: none; }
body.queimado .pagina:not(.queimada) { display: none; }
body.queimado .pagina.queimada { display: block; }
body.queimado { background: radial-gradient(ellipse at 50% 115%, rgba(255, 90, 20, .25), transparent 60%) fixed, #0d0806; }
.pagina.queimada { padding: 0; background: none; box-shadow: none;
  --papel: #d6bf92; --papel-2: #c4a26c; --tinta: #2a1a10; --tinta-suave: #5e4430; --vermelho: #8a1c0c;
  --linha: rgba(90, 60, 30, .2); --margem: rgba(120, 40, 20, .35);
  filter: drop-shadow(0 0 5px rgba(255, 110, 30, .5)); animation: brasa 3.4s ease-in-out infinite; }
.folha { position: relative; padding: 46px 44px 52px 84px;
  background: linear-gradient(90deg, transparent 63px, var(--margem) 63px 65px, transparent 65px),
    repeating-linear-gradient(transparent 0 31px, var(--linha) 31px 32px),
    radial-gradient(ellipse at 50% 45%, var(--papel) 40%, var(--papel-2) 75%, #7a4e24 92%, #2a1308 100%);
  background-position: 0 0, 0 8px, 0 0; color: var(--tinta);
  box-shadow: inset 0 0 50px rgba(80, 32, 8, .75), inset 0 0 14px rgba(25, 10, 3, .9); }
.folha.capa { min-height: 360px; }
.folha.ultima { min-height: 300px; display: flex; align-items: center; }
.cinza { color: transparent; border-radius: 45% 55% 40% 60%; padding: 0 2px;
  background: radial-gradient(ellipse, #160a04 35%, #4a2410 62%, rgba(255, 120, 30, .55) 72%, transparent 80%); }
.furo { position: absolute; z-index: 2; pointer-events: none; border-radius: 47% 53% 41% 59% / 55% 44% 56% 45%;
  background: radial-gradient(circle, #0d0806 0 46%, #2a0f04 54%, rgba(255, 120, 30, .85) 60%,
    rgba(140, 60, 15, .5) 67%, transparent 74%); }
.luz.fogo-btn { bottom: 64px; background: #2a1208; color: #ffcf9a; border-color: #c2541c; }
.fogo-tela { position: fixed; left: 0; right: 0; bottom: 0; height: 220vh; z-index: 13; pointer-events: none;
  opacity: 0; transform: translateY(100%);
  background: linear-gradient(to top, #050302 0 38%, #2a0a02 46%, #a8320a 52%, #ff8a1e 56%, #ffd98a 58%,
    rgba(255, 140, 40, .35) 62%, transparent 70%); }
body.pegando-fogo .fogo-tela { animation: subir 2.6s ease-in forwards; }
@keyframes subir { 0% { transform: translateY(100%); opacity: 1; } 55% { transform: translateY(-12%); opacity: 1; }
  100% { transform: translateY(-12%); opacity: 0; } }
@keyframes brasa { 0%, 100% { filter: drop-shadow(0 0 4px rgba(255, 110, 30, .45)); }
  50% { filter: drop-shadow(0 0 10px rgba(255, 140, 40, .7)); } }
@media (prefers-reduced-motion: reduce) { .tremido { animation: none; } .pagina.queimada { animation: none; }
  body.pegando-fogo .fogo-tela { animation: none; } }
@media (max-width: 640px) {
  body { padding: 20px 16px 100px; font-size: 17px; }
  .pagina { padding: 32px 18px 28px 40px;
    background: linear-gradient(90deg, transparent 27px, var(--margem) 27px 29px, transparent 29px),
      repeating-linear-gradient(transparent 0 31px, var(--linha) 31px 32px), linear-gradient(170deg, var(--papel), var(--papel-2));
    background-position: 0 0, 0 8px, 0 0; }
  h1 { font-size: 54px; }
  h2 { font-size: 36px; line-height: 48px; }
  .lado-a-lado { grid-template-columns: 1fr; }
  .vulto { margin: 0 auto; }
  .indice { columns: 1; }
  .rotulo { right: 16px; }
  .uv { font-size: 24px; line-height: 28px; max-width: 80%; }
  .folha { padding: 36px 20px 40px 40px; }
  .luz.fogo-btn { bottom: 64px; }
  .uv-2 { left: 44px; }
}
"""

JS = """
(function () {
  var corpo = document.body, botoes = document.querySelectorAll('.luz');
  var texto = {escuro: ['apagar a luz', 'acender a luz'], 'uv-on': ['luz negra', 'luz normal'],
               queimado: ['riscar um fósforo', 'o caderno de antes']};
  var mx = innerWidth / 2, my = innerHeight * 0.45;
  function mover(x, y) { mx = x; my = y; corpo.style.setProperty('--mx', x + 'px'); corpo.style.setProperty('--my', y + 'px'); }
  var sombra = document.querySelector('.aparicao'), clarao = document.querySelector('.clarao');
  function aparecer(ms) {  /* ele, na beira da luz, enquanto a lanterna falha */
    var lado = Math.random() < .5 ? -1 : 1;
    sombra.classList.remove('grande');
    sombra.style.left = (mx + lado * (55 + Math.random() * 50) - 55) + 'px';  /* meio dentro da luz */
    sombra.style.top = (my - 150 + Math.random() * 40) + 'px';
    sombra.classList.add('ve');
    setTimeout(function () { sombra.classList.remove('ve'); }, ms);
  }
  var cliques = [], viu = false;
  function inteiro() {  /* quem pisca a lanterna demais chama: ele aparece inteiro, uma vez */
    viu = true;
    if (!calmo) { clarao.classList.add('ve'); setTimeout(function () { clarao.classList.remove('ve'); }, 70); }
    sombra.classList.add('grande', 've');
    setTimeout(function () { sombra.classList.remove('ve', 'grande'); corpo.classList.add('visto'); }, 650);
  }
  function sorte(a, b) { return a + Math.random() * (b - a); }
  function espalhar() {  /* a tinta UV nunca esta no mesmo lugar: recados e maos se espalham a cada vez */
    document.querySelectorAll('.uv').forEach(function (el) {
      el.style.right = 'auto'; el.style.bottom = 'auto';
      el.style.top = sorte(6, 82) + '%'; el.style.left = sorte(8, 42) + '%';
      el.style.transform = 'rotate(' + sorte(-12, 12).toFixed(1) + 'deg)';
    });
    document.querySelectorAll('.pagina').forEach(function (pag) {
      var maos = pag.querySelectorAll('.uv-mao');
      if (!maos.length) return;
      if (maos.length < 2) {
        var c = maos[0].cloneNode(true); c.classList.add('extra'); pag.appendChild(c);
        maos = pag.querySelectorAll('.uv-mao');
      }
      maos.forEach(function (m, i) {
        var some = i > 0 && Math.random() < .5;  /* as vezes, uma segunda mao */
        m.style.display = some ? 'none' : '';
        m.style.left = sorte(4, 84) + '%'; m.style.top = sorte(8, 82) + '%'; m.style.bottom = 'auto';
        m.style.width = sorte(34, 62).toFixed(0) + 'px';
        m.style.transform = 'rotate(' + sorte(-45, 45).toFixed(0) + 'deg)' + (Math.random() < .5 ? ' scaleX(-1)' : '');
      });
    });
  }
  espalhar();
  var olhos = [];
  function lugar(o) { o.style.left = (20 + Math.random() * (innerWidth - 60)) + 'px';
    o.style.top = (20 + Math.random() * (innerHeight - 40)) + 'px'; }
  for (var i = 0; i < 6; i++) {  /* olhos no escuro: somem quando a luz chega perto */
    var o = document.createElement('div'); o.className = 'olho-par vivo'; o.setAttribute('aria-hidden', 'true');
    lugar(o); document.body.appendChild(o); olhos.push(o);
  }
  setInterval(function () {
    if (!corpo.classList.contains('escuro')) return;
    olhos.forEach(function (o) {
      var r = o.getBoundingClientRect(), d = Math.hypot(r.left + 10 - mx, r.top + 3 - my);
      if (d < 175 && o.classList.contains('vivo')) {
        o.classList.remove('vivo');
        setTimeout(function () { lugar(o); o.classList.add('vivo'); }, 2000 + Math.random() * 2500);
      } else if (o.classList.contains('vivo') && Math.random() < .03) {  /* piscam */
        o.classList.remove('vivo'); setTimeout(function () { o.classList.add('vivo'); }, 160);
      }
    });
  }, 250);
  addEventListener('pointermove', function (e) { mover(e.clientX, e.clientY); });
  addEventListener('touchmove', function (e) { var t = e.touches[0]; if (t) mover(t.clientX, t.clientY); }, {passive: true});
  var calmo = matchMedia('(prefers-reduced-motion: reduce)').matches, relogio = null;
  function falhar() {  /* de vez em quando a lanterna falha -- como no jogo */
    if (!corpo.classList.contains('escuro') || calmo) return;
    var ms = 90 + Math.random() * 160;
    corpo.classList.add('pisca');
    if (Math.random() < .6) aparecer(ms + 40);
    setTimeout(function () { corpo.classList.remove('pisca'); }, ms);
  }
  function queimar(botao) {  /* o caderno pega fogo: a chama sobe pela tela; o que sobra e o pesadelo */
    corpo.classList.add('pegando-fogo');
    setTimeout(function () {
      corpo.classList.add('queimado'); botao.textContent = texto.queimado[1];
      var capa = document.getElementById('q-capa'); if (capa) capa.scrollIntoView();
    }, calmo ? 0 : 1450);
    setTimeout(function () { corpo.classList.remove('pegando-fogo'); }, calmo ? 0 : 2700);
  }
  botoes.forEach(function (botao) {  /* apagar a luz (lanterna) ou luz negra (le a tinta UV): um modo por vez */
    botao.addEventListener('click', function () {
      var modo = botao.dataset.modo, ligar = !corpo.classList.contains(modo), agora = Date.now();
      if (modo === 'escuro') {
        cliques = cliques.filter(function (t) { return agora - t < 4000; }).concat([agora]);
        if (cliques.length >= 5 && !viu) setTimeout(inteiro, 120);
      }
      var estava = corpo.classList.contains('queimado');
      corpo.classList.remove('escuro', 'uv-on', 'queimado');
      botoes.forEach(function (b) { b.textContent = texto[b.dataset.modo][0]; });
      if (ligar && modo === 'queimado') queimar(botao);
      else if (ligar) { corpo.classList.add(modo); botao.textContent = texto[modo][1]; }
      if (estava && !ligar) { var capa = document.getElementById('capa'); if (capa) capa.scrollIntoView(); }
      if (ligar && modo === 'uv-on') espalhar();
      clearInterval(relogio);
      if (ligar && modo === 'escuro') relogio = setInterval(function () { if (Math.random() < .25) falhar(); }, 2500);
    });
  });
})();
"""

# os recados em tinta ultravioleta: so aparecem com a "luz negra". Outra letra.
UV: dict[str, list[str]] = {
    "capa": ["não devolve. fica comigo."], "indice": ["você já leu isso antes."], "antes": ["você já veio antes."],
    "lanterna": ["ele gosta quando a luz pisca"], "ele": ["ele também procura alguém"],
    "ouve": ["eu ouço você daqui"], "respirar": ["conta até seis. no sete ele vira."],
    "omamori": ["o oitavo é o meu"], "mapa": ["o mapa tá ao contrário"], "papeis": ["o guizo era eu"],
    "armadilhas": ["eu sei onde estão todas"], "ritmo": ["quando os grilos voltam eu durmo"],
    "aprende": ["ele aprendeu comigo"], "mente": ["as pegadas são suas. da outra vez."],
    "nomes": ["o sétimo é o seu"], "sinalizador": ["vermelho dói no olho dele"],
    "esconder": ["o poço é meu. não entra."], "camera": ["sorri"],
    "ayame": ["por que você não corre mais rápido?"], "pequena": ["ela não sou eu"],
    "noite": ["na chuva eu chego mais perto"], "oitavo": ["leva. eu tô esperando."],
    "arrozais": ["a água guarda o som"], "cego": ["ele era bom. antes."],
    "aldeia": ["a quinta pessoa sou eu"], "imitadora": ["eu nunca chorei. nunca."],
    "bambuzal": ["o cortador sou eu"], "farejador": ["ele lambe devagar. sem pressa."],
    "cemiterio": ["o quinto nome é o seu"], "fantoche": ["ela me carregou no colo. antes."],
    "escola": ["a carteira que falta é a minha"], "torii": ["um. dois. três. ainda tô contando."],
    "pesadelo": ["a gente nunca parou de brincar"], "terceira": ["de novo"], "ultima": ["acorda"],
}


# escrita a lapis, fraca: so aparece com a luz apagada (dentro do circulo da lanterna)
ESCURO: dict[str, str] = {
    "ele": "ele esta atras de voce agora.",
    "lanterna": "nao olhe para tras quando ela piscar.",
    "mente": "conte as paginas deste caderno. conte de novo.",
    "esconder": "ele ja sabe onde voce vai se esconder.",
    "imitadora": "a de verdade nunca escreveu neste caderno.",
    "fantoche": "nao olhe para as costas dela por muito tempo. a coisa olha de volta.",
    "pequena": "ela nao quer te pegar. quer a sua lanterna.",
    "torii": "o setimo lugar e o seu.",
}
MAOS = ("capa", "antes", "nomes", "ayame", "farejador", "fantoche", "ultima")  # maos pequenas, so na luz negra

MAO_SVG = (
    '<svg viewBox="0 0 40 50" class="mao-svg"><path d="M12,48 q-8,-14 -6,-24 q1,-4 4,-1 l2,8 l0,-22 '
    'q2,-4 4,0 l1,18 l1,-22 q2,-4 4,0 l0,22 l2,-19 q2,-4 4,0 l-1,21 l4,-12 q3,-3 4,1 l-5,20 q-3,10 -12,10 z"/></svg>')

PAGINA_ARRANCADA = """<section class="pagina arrancada" id="arrancada" aria-label="pagina arrancada">
<span class="rotulo">a pagina que eu arranquei</span>
<div class="uv-texto">
<p>Nao vim buscar a Ayame. Vim devolver.</p>
<p>Naquela noite a gente brincou de esconde-esconde na floresta. Eu contei ate dez, de olhos fechados,
encostado no torii.</p>
<p>Ela nao voltou.</p>
<p>Eu fui para casa e nao contei para ninguem.</p>
<p>O oitavo omamori e o dela. Ela me deu "para voce me achar depois".</p>
<p>Quem deve na conta da floresta sou eu. Se eu deixar o oitavo no altar todas as noites, talvez
o rio me deixe passar.</p>
<p>Na margem do rio, no escuro, ela cantarola a musica da roda. Se a luz achar ela de longe, nao vale.
Tem que chegar perto, e dizer.</p>
</div>
</section>"""

# o vulto, recortado em preto, com os olhos acesos: aparece quando a lanterna falha
SOMBRA_SVG = (
    '<svg viewBox="0 0 120 300" class="sombra-svg">'
    '<ellipse cx="54" cy="52" rx="14" ry="24" transform="rotate(-22 54 52)"/>'
    '<path d="M58,72 q-2,12 -1,24 l-17,0 q-12,62 -8,120 l6,14 l4,-14 q2,-50 6,-90 l-2,76 l-6,98 l12,0 l8,-96 '
    'l8,96 l12,0 l-6,-98 l-2,-76 q4,40 6,90 l4,14 l6,-14 q4,-58 -8,-120 l-17,0 q1,-12 -1,-24 z"/>'
    '<circle cx="47" cy="50" r="2.6" class="olho-vermelho"/><circle cx="58" cy="46" r="2.6" class="olho-vermelho"/>'
    '</svg>')


def escuro(pid: str) -> str:
    return f'<p class="lapis" aria-hidden="true">{html.escape(ESCURO[pid])}</p>' if pid in ESCURO else ""


def maos(pid: str) -> str:
    return f'<div class="uv-mao" aria-hidden="true">{MAO_SVG}</div>' if pid in MAOS else ""


def uv(pid: str) -> str:
    return "".join(f'<p class="uv uv-{k % 3}" aria-hidden="true">{html.escape(t)}</p>' for k, t in enumerate(UV.get(pid, [])))


FONTES = ("https://fonts.googleapis.com/css2?family=Caveat:wght@400;700&family=Kalam:wght@400;700"
          "&family=Special+Elite&display=swap")


def gerar() -> str:
    m = mapa.gerar_mapa()
    pags = paginas(m)
    indice = "".join(f'<li><a href="#{pid}">{html.escape(titulo)}</a></li>' for pid, _, titulo, _ in pags if titulo)
    corpo = [f"""<section class="pagina capa" id="capa">
<p class="sub">se encontrar, {_dia_noite("devolva", "não devolva")} ao santuário</p>
<h1>Diário</h1>
<p class="sub">floresta ao sul da aldeia · outono</p>
<p class="aviso">não leia de noite</p>
{uv("capa")}{maos("capa")}
</section>
<section class="pagina" id="indice"><span class="rotulo">índice</span>
<h2>O que tem aqui</h2>
<ol class="indice">{indice}</ol>
<p class="nota">{_dia_noite("tudo", "nada")} o que está escrito aqui aconteceu. os números eu medi contando.</p>
{uv("indice")}
</section>"""]
    for pid, rotulo, titulo, conteudo in pags:
        classe = "pagina ultima" if not titulo else "pagina"
        cab = f'<span class="rotulo">{html.escape(rotulo)}</span>\n<h2>{html.escape(titulo)}</h2>' if titulo else ""
        if pid == "ultima":
            corpo.append(PAGINA_ARRANCADA)  # fora do indice: so aparece com a luz negra
        corpo.append(f'<section class="{classe}" id="{pid}">{cab}{conteudo.strip()}\n{escuro(pid)}{uv(pid)}'
                     f'{maos(pid)}</section>')
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Diário da floresta</title>
<!-- Gerado por python tools/gerar_diario.py a partir do codigo e dos dados do jogo. Nao edite aqui. -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTES}">
<style>{CSS}</style>
</head>
<body>
{chr(10).join(corpo)}
{caderno_queimado()}
<a class="topo" href="#indice">↑ índice</a>
<button class="luz" type="button" data-modo="escuro">apagar a luz</button>
<button class="luz uv-btn" type="button" data-modo="uv-on">luz negra</button>
<button class="luz fogo-btn" type="button" data-modo="queimado">riscar um fósforo</button>
<div class="fogo-tela" aria-hidden="true"></div>
<div class="aparicao" aria-hidden="true">{SOMBRA_SVG}</div>
<div class="clarao" aria-hidden="true"></div>
<script>{JS}</script>
</body>
</html>
"""


def main() -> None:
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(gerar(), encoding="utf-8")
    print(f"escrito: {DESTINO.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
