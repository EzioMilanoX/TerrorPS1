# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Os sons da demo, sintetizados (sem arquivos de fora) e salvos como WAV na primeira vez.

No terror o som e metade do medo -- e a pista justa que o blueprint SEN-03 pede: o vulto
nao aparece no escuro, mas o galho que ele quebra estala do lado em que ele esta.
"""
from __future__ import annotations

import wave
from collections.abc import Callable
from pathlib import Path

import numpy as np

TAXA = 22050
VERSAO = "9"


def _ruido(n: int, rng) -> np.ndarray:
    return rng.uniform(-1, 1, n)


def _passa_baixa(x: np.ndarray, k: float) -> np.ndarray:
    """Filtro de um polo: k pequeno = mais abafado."""
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += k * (v - acc)
        y[i] = acc
    return y


def _env(n: int, ataque: float, queda: float) -> np.ndarray:
    t = np.arange(n) / TAXA
    return np.minimum(1.0, t / max(ataque, 1e-4)) * np.exp(-t / queda)


def passo(rng) -> np.ndarray:
    n = int(0.16 * TAXA)
    terra = _passa_baixa(_ruido(n, rng), 0.25) * _env(n, 0.004, 0.035)
    cascalho = _ruido(n, rng) * (rng.uniform(size=n) > 0.985) * _env(n, 0.01, 0.05)  # pedrinhas
    return 0.9 * terra + 0.35 * cascalho


def clique(rng) -> np.ndarray:
    n = int(0.05 * TAXA)
    t = np.arange(n) / TAXA
    return (0.6 * np.sin(2 * np.pi * 2400 * t) + 0.4 * _ruido(n, rng)) * _env(n, 0.0005, 0.006)


def batida(rng) -> np.ndarray:
    """Tum-tum: duas pancadas graves."""
    n = int(0.5 * TAXA)
    t = np.arange(n) / TAXA
    som = np.zeros(n)
    for inicio, forca in ((0.0, 1.0), (0.17, 0.7)):
        tt = np.clip(t - inicio, 0, None)
        f = 55 + 25 * np.exp(-tt / 0.03)  # a altura cai: o "baque"
        som += forca * np.sin(2 * np.pi * np.cumsum(f) / TAXA) * (t >= inicio) * np.exp(-tt / 0.07)
    return som


def galho(rng) -> np.ndarray:
    """O galho que quebra quando o vulto anda no escuro: estalos secos e um ranger."""
    n = int(0.45 * TAXA)
    som = np.zeros(n)
    for _ in range(4):
        i = int(rng.uniform(0, 0.12) * TAXA)
        m = int(0.02 * TAXA)
        som[i:i + m] += _ruido(m, rng) * _env(m, 0.0003, 0.004) * rng.uniform(0.5, 1.0)
    t = np.arange(n) / TAXA
    ranger = np.sin(2 * np.pi * (180 + 60 * np.sin(2 * np.pi * 7 * t)) * t) * _env(n, 0.05, 0.12)
    return som + 0.25 * ranger * (_passa_baixa(_ruido(n, rng), 0.3) + 0.5)


def pegou(rng) -> np.ndarray:
    n = int(1.4 * TAXA)
    t = np.arange(n) / TAXA
    grito = np.sin(2 * np.pi * (300 + 900 * t) * t) * 0.5 + _ruido(n, rng)
    return np.tanh(3 * grito) * _env(n, 0.002, 0.45) * 0.7


def zumbido(rng) -> np.ndarray:
    """8 s em laco perfeito: dois graves quase iguais (batem) e um vento abafado."""
    n = 8 * TAXA
    t = np.arange(n) / TAXA
    grave = 0.5 * np.sin(2 * np.pi * 41 * t) + 0.4 * np.sin(2 * np.pi * 41.5 * t) + 0.15 * np.sin(2 * np.pi * 82.25 * t)
    vento = _passa_baixa(_ruido(n, rng), 0.02) * 6
    sopro = 0.6 + 0.4 * np.sin(2 * np.pi * t / 8)  # o vento cresce e cai no mesmo laco
    som = 0.5 * grave + 0.5 * vento * sopro
    m = int(0.5 * TAXA)  # emenda: o fim se mistura com o comeco
    som[:m] = som[:m] * np.linspace(0, 1, m) + som[-m:] * np.linspace(1, 0, m)
    return som[:-m]


def armadilha(rng) -> np.ndarray:
    """O estalo da armadilha: metal batendo em metal, com o zumbido da mola."""
    n = int(0.9 * TAXA)
    t = np.arange(n) / TAXA
    metal = sum(np.sin(2 * np.pi * f * t) * a for f, a in ((523, 1.0), (1187, 0.6), (2311, 0.4), (3790, 0.25)))
    pancada = _ruido(n, rng) * _env(n, 0.0002, 0.012) * 2.0
    return np.tanh(2.0 * (metal * _env(n, 0.0005, 0.18) + pancada))


def sino(rng) -> np.ndarray:
    """O guizo do amuleto: tilintar agudo e fino, a pista de onde ele esta."""
    n = int(1.2 * TAXA)
    t = np.arange(n) / TAXA
    som = np.zeros(n)
    for atraso in (0.0, 0.11, 0.19):
        tt = np.clip(t - atraso, 0, None)
        tom = sum(np.sin(2 * np.pi * f * tt) * a for f, a in ((1760, 1.0), (2637, 0.5), (4186, 0.3)))
        som += tom * (t >= atraso) * np.exp(-tt / 0.25)
    return som


def coleta(rng) -> np.ndarray:
    n = int(0.6 * TAXA)
    t = np.arange(n) / TAXA
    return (np.sin(2 * np.pi * 880 * t) + 0.6 * np.sin(2 * np.pi * 1320 * t)) * _env(n, 0.005, 0.2)


def forca(rng) -> np.ndarray:
    """Forcando a armadilha: metal rangendo."""
    n = int(0.25 * TAXA)
    t = np.arange(n) / TAXA
    return np.sin(2 * np.pi * (300 + 200 * np.sin(2 * np.pi * 23 * t)) * t) * _env(n, 0.02, 0.08) + 0.3 * _ruido(n, rng) * _env(n, 0.01, 0.05)


def roda(rng) -> np.ndarray:
    """A musica da roda: tres criancas cantarolando, sem palavras e nao muito afinadas, uma
    melodia de cinco notas, devagar. A ultima nota fica no ar, sem resolver (~7,6 s)."""
    notas = ((0, 1), (3, 1), (5, 1), (3, 1), (0, 2), (-2, 1), (0, 1), (3, 1), (7, 1), (5, 2), (3, 1), (0, 1),
             (3, 1), (5, 3))
    batida = 0.42
    total = sum(d for _, d in notas) * batida + 0.4
    n = int(total * TAXA)
    som = np.zeros(n)
    inicio = 0.0
    for semi, dur in notas:
        f0 = 392.0 * 2 ** (semi / 12)
        i0, i1 = int(inicio * TAXA), min(n, int((inicio + dur * batida + 0.08) * TAXA))
        tt = np.arange(i1 - i0) / TAXA
        env = np.minimum(1.0, tt / 0.06) * np.minimum(1.0, (tt[-1] - tt) / 0.08 + 1e-3)
        for k, desafina in enumerate((1.0, 1.006, 0.993)):
            vib = 1 + 0.008 * np.sin(2 * np.pi * (5.0 + k * 0.7) * tt)
            fase = 2 * np.pi * f0 * desafina * np.cumsum(vib) / TAXA
            som[i0:i1] += (np.sin(fase) + 0.3 * np.sin(2 * fase)) * env * 0.33
        inicio += dur * batida
    return som + _passa_baixa(_ruido(n, rng), 0.05) * 0.05


def amanhecer(rng) -> np.ndarray:
    """O fim: um acorde que abre devagar."""
    n = 4 * TAXA
    t = np.arange(n) / TAXA
    acorde = sum(np.sin(2 * np.pi * f * t) for f in (220.0, 277.18, 329.63, 440.0))
    return acorde * np.minimum(1.0, t / 1.5) * np.exp(-np.clip(t - 2.0, 0, None) / 0.8)


def grilos(rng) -> np.ndarray:
    """1 s de grilos (repetido em laco pela cena): cricrilados agudos em grupos de tres.
    Curto de proposito: quando a floresta cala, cala em menos de um segundo."""
    n = TAXA
    t = np.arange(n) / TAXA
    som = np.zeros(n)
    for voz, (f, inicio) in enumerate(((4300.0, 0.05), (4700.0, 0.4), (4050.0, 0.7))):
        for k in range(3):
            tt = t - (inicio + k * 0.055 + rng.uniform(0, 0.01))
            janela = (tt >= 0) & (tt < 0.035)
            som += np.where(janela, np.sin(2 * np.pi * f * tt) * np.sin(np.pi * np.clip(tt / 0.035, 0, 1)), 0) * (1 - 0.2 * voz)
    return som


def sapo(rng) -> np.ndarray:
    n = int(0.5 * TAXA)
    t = np.arange(n) / TAXA
    pulso = (np.sin(2 * np.pi * 28 * t) > 0.2).astype(float)  # o coaxar: um ronco pulsado
    return np.sin(2 * np.pi * (180 + 40 * t) * t) * pulso * _env(n, 0.02, 0.18)


def coruja(rng) -> np.ndarray:
    """Hu... hu-huu: grave, oco, longe."""
    n = int(1.6 * TAXA)
    t = np.arange(n) / TAXA
    som = np.zeros(n)
    for inicio, dur, f in ((0.0, 0.32, 390.0), (0.55, 0.14, 380.0), (0.75, 0.5, 400.0)):
        tt = t - inicio
        janela = (tt >= 0) & (tt < dur)
        som += np.where(janela, np.sin(2 * np.pi * f * tt) * np.sin(np.pi * np.clip(tt / dur, 0, 1)) ** 0.7, 0)
    return _passa_baixa(som + 0.03 * _ruido(n, rng), 0.35)


def respiracao(rng) -> np.ndarray:
    """Uma respiracao ofegante: o ar entrando e saindo pela boca."""
    n = TAXA
    t = np.arange(n) / TAXA
    ar = _passa_baixa(_ruido(n, rng), 0.12) * 3
    entra = np.sin(np.pi * np.clip(t / 0.4, 0, 1)) * 0.7
    sai = np.sin(np.pi * np.clip((t - 0.45) / 0.5, 0, 1)) * (t > 0.45)
    return ar * (entra + sai)


def arfar(rng) -> np.ndarray:
    """Nao aguentou prender: o ar entra de uma vez, alto, e sai tremendo."""
    n = int(1.3 * TAXA)
    t = np.arange(n) / TAXA
    ar = _passa_baixa(_ruido(n, rng), 0.25) * 3
    entra = np.sin(np.pi * np.clip(t / 0.35, 0, 1)) ** 0.5 * (t < 0.35)
    sai = (t >= 0.45) * np.exp(-np.clip(t - 0.45, 0, None) / 0.4) * (0.7 + 0.3 * np.sin(2 * np.pi * 9 * t))
    return ar * (1.3 * entra + 0.8 * sai)


def tilintar(rng) -> np.ndarray:
    """Os amuletos batendo um no outro no bolso."""
    n = int(0.25 * TAXA)
    t = np.arange(n) / TAXA
    som = np.zeros(n)
    for _ in range(3):
        t0 = rng.uniform(0, 0.08)
        tt = np.clip(t - t0, 0, None)
        som += (t >= t0) * np.sin(2 * np.pi * rng.uniform(2600, 3600) * tt) * np.exp(-tt / 0.03)
    return som


def graveto(rng) -> np.ndarray:
    """O graveto que voce pisa: um estalo seco, alto, perto."""
    n = int(0.3 * TAXA)
    som = np.zeros(n)
    for k in range(3):
        i = int((0.004 + k * 0.012 + rng.uniform(0, 0.006)) * TAXA)
        m = int(0.015 * TAXA)
        som[i:i + m] += _ruido(m, rng) * _env(m, 0.0002, 0.003) * (1.0 - 0.25 * k)
    return som + 0.15 * _passa_baixa(_ruido(n, rng), 0.4) * _env(n, 0.001, 0.04)


def sinalizador(rng) -> np.ndarray:
    """O sinalizador aceso: o chiado forte e a chama crepitando ate apagar (10 s)."""
    n = 10 * TAXA
    t = np.arange(n) / TAXA
    chama = _ruido(n, rng) * (0.55 + 0.15 * np.sin(2 * np.pi * 3.1 * t)) * np.minimum(1.0, t / 0.08)
    estalos = _ruido(n, rng) * (rng.uniform(size=n) > 0.9993) * 4
    return (0.6 * chama + estalos) * np.clip((10.0 - t) / 1.5, 0, 1)


def chiado(rng) -> np.ndarray:
    """A lanterna falhando: zumbido eletrico com estalos."""
    n = int(0.8 * TAXA)
    t = np.arange(n) / TAXA
    zum = np.sign(np.sin(2 * np.pi * 120 * t)) * 0.3 + 0.4 * _ruido(n, rng) * (rng.uniform(size=n) > 0.97)
    return zum * _env(n, 0.005, 0.4)


def foto(rng) -> np.ndarray:
    """A camera: o clique do obturador e o zumbido do flash recarregando."""
    n = int(1.2 * TAXA)
    t = np.arange(n) / TAXA
    clique_ = _ruido(n, rng) * _env(n, 0.0003, 0.008) * 1.5
    carga = np.sin(2 * np.pi * (2000 + 3500 * t / 1.2) * t) * 0.25 * (t > 0.15) * np.clip((1.2 - t) / 0.3, 0, 1)
    return clique_ + carga


def chuva(rng) -> np.ndarray:
    """2 s de chuva na mata (repetido pela cena): chiado largo e gotas nas folhas."""
    n = 2 * TAXA
    som = _passa_baixa(_ruido(n, rng), 0.35) * 1.5
    gotas = _ruido(n, rng) * (rng.uniform(size=n) > 0.997) * 2.5
    m = int(0.2 * TAXA)  # emenda para o laco nao estalar
    som[:m] = som[:m] * np.linspace(0, 1, m) + som[-m:] * np.linspace(1, 0, m)
    return (som + gotas)[:-m]


def passinhos(rng) -> np.ndarray:
    """Passos curtos e rapidos de crianca correndo no mato."""
    n = int(1.2 * TAXA)
    som = np.zeros(n)
    for k in range(6):
        i = int((k * 0.18 + rng.uniform(0, 0.03)) * TAXA)
        m = int(0.06 * TAXA)
        som[i:i + m] += _passa_baixa(_ruido(m, rng), 0.3) * _env(m, 0.003, 0.02) * rng.uniform(0.6, 1.0)
    return som


def estalos(rng) -> np.ndarray:
    """A pequena se mexendo: juntas estalando, secas."""
    n = int(0.35 * TAXA)
    som = np.zeros(n)
    for _ in range(4):
        i = int(rng.uniform(0, 0.25) * TAXA)
        m = int(0.008 * TAXA)
        som[i:i + m] += _ruido(m, rng) * _env(m, 0.0001, 0.0015)
    return som


def esconder(rng) -> np.ndarray:
    """Pano e madeira: entrar ou sair do esconderijo."""
    n = int(0.6 * TAXA)
    t = np.arange(n) / TAXA
    return _passa_baixa(_ruido(n, rng), 0.2) * 2 * np.sin(np.pi * np.clip(t / 0.6, 0, 1))


def agua(rng) -> np.ndarray:
    """Um passo na agua rasa: o pe entrando e o espirro."""
    n = int(0.35 * TAXA)
    t = np.arange(n) / TAXA
    entra = _passa_baixa(_ruido(n, rng), 0.15) * _env(n, 0.005, 0.05) * 2.5
    gotas = _ruido(n, rng) * (rng.uniform(size=n) > 0.992) * _env(n, 0.02, 0.12) * 3
    bolha = np.sin(2 * np.pi * (500 + 900 * t) * t) * _env(n, 0.01, 0.04) * 0.3
    return entra + gotas + bolha


def cego_passo(rng) -> np.ndarray:
    """O passo dele: grave, pesado, a agua se abrindo."""
    n = int(0.6 * TAXA)
    t = np.arange(n) / TAXA
    baque = np.sin(2 * np.pi * (48 + 30 * np.exp(-t / 0.05)) * t) * _env(n, 0.003, 0.14)
    agua_ = _passa_baixa(_ruido(n, rng), 0.12) * _env(n, 0.02, 0.18) * 2.2
    return baque + agua_


def gemido(rng) -> np.ndarray:
    """Quando ele ouve: um gemido longo, grave, que sobe."""
    n = int(1.8 * TAXA)
    t = np.arange(n) / TAXA
    f = 70 + 40 * t / 1.8
    voz = np.sin(2 * np.pi * np.cumsum(f) / TAXA) + 0.5 * np.sin(2 * np.pi * np.cumsum(2.01 * f) / TAXA)
    rouco = _passa_baixa(_ruido(n, rng), 0.08) * 2
    return np.tanh(1.5 * (voz + rouco)) * np.sin(np.pi * np.clip(t / 1.8, 0, 1)) ** 0.6


def sapos(rng) -> np.ndarray:
    """2 s do coro de sapos dos arrozais (repetido pela cena)."""
    n = 2 * TAXA
    t = np.arange(n) / TAXA
    som = np.zeros(n)
    for _ in range(9):
        f, t0, dur = rng.uniform(220, 420), rng.uniform(0, 1.7), rng.uniform(0.12, 0.3)
        tt = t - t0
        janela = (tt >= 0) & (tt < dur)
        pulso = (np.sin(2 * np.pi * rng.uniform(18, 30) * tt) > 0).astype(float)
        som += np.where(janela, np.sin(2 * np.pi * f * tt) * pulso * np.sin(np.pi * np.clip(tt / dur, 0, 1)), 0)
    return som


def choro(rng) -> np.ndarray:
    """Uma crianca chorando baixinho, longe: soluços com a voz tremendo."""
    n = int(2.4 * TAXA)
    t = np.arange(n) / TAXA
    som = np.zeros(n)
    for k in range(4):
        t0 = 0.1 + k * 0.55 + rng.uniform(0, 0.08)
        tt = t - t0
        dur = rng.uniform(0.3, 0.45)
        janela = (tt >= 0) & (tt < dur)
        f = 520 - 140 * np.clip(tt / dur, 0, 1) + 18 * np.sin(2 * np.pi * 7 * tt)
        voz = np.sin(2 * np.pi * np.cumsum(f) / TAXA) + 0.4 * np.sin(4 * np.pi * np.cumsum(f) / TAXA)
        som += np.where(janela, voz * np.sin(np.pi * np.clip(tt / dur, 0, 1)), 0)
    return _passa_baixa(som + 0.05 * _ruido(n, rng), 0.3)


def corte(rng) -> np.ndarray:
    """O toco entrando na canela: um rasgo curto e um gemido abafado."""
    n = int(0.7 * TAXA)
    t = np.arange(n) / TAXA
    rasgo = _passa_baixa(_ruido(n, rng), 0.5) * _env(n, 0.002, 0.05) * 1.5
    gemido = np.sin(2 * np.pi * (180 - 40 * t) * t) * _env(n, 0.06, 0.25) * (t > 0.08) * 0.6
    return rasgo + gemido


def farejar(rng) -> np.ndarray:
    """Ele cheirando o chao: tres fungadas rapidas e molhadas."""
    n = int(0.9 * TAXA)
    som = np.zeros(n)
    for k in range(3):
        i = int((0.05 + k * 0.17 + rng.uniform(0, 0.03)) * TAXA)
        m = int(0.12 * TAXA)
        tt = np.arange(m) / TAXA
        som[i:i + m] += _passa_baixa(_ruido(m, rng), 0.25) * np.sin(np.pi * np.clip(tt / 0.12, 0, 1)) * 2.5
    return som


SONS: dict[str, Callable] = {"passo": passo, "clique": clique, "batida": batida, "galho": galho,
                             "pegou": pegou, "zumbido": zumbido, "armadilha": armadilha, "sino": sino,
                             "coleta": coleta, "forca": forca, "amanhecer": amanhecer, "grilos": grilos,
                             "sapo": sapo, "coruja": coruja, "respiracao": respiracao, "arfar": arfar,
                             "tilintar": tilintar, "graveto": graveto, "sinalizador": sinalizador, "chiado": chiado,
                             "foto": foto, "chuva": chuva, "passinhos": passinhos, "estalos": estalos,
                             "esconder": esconder, "agua": agua, "cego_passo": cego_passo, "gemido": gemido,
                             "sapos": sapos, "choro": choro, "corte": corte, "farejar": farejar, "roda": roda}


def _salvar(caminho: Path, som: np.ndarray) -> None:
    som = som / (np.abs(som).max() + 1e-9) * 0.9
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TAXA)
        w.writeframes((som * 32767).astype("<i2").tobytes())


def gerar(pasta: Path) -> dict[str, Path]:
    """Gera (so na primeira vez, ou se `VERSAO` mudar) e devolve id -> caminho do WAV."""
    pasta.mkdir(parents=True, exist_ok=True)
    caminhos = {nome: pasta / f"{nome}_v{VERSAO}.wav" for nome in SONS}
    for nome, f in SONS.items():
        if not caminhos[nome].exists():
            _salvar(caminhos[nome], f(np.random.default_rng(len(nome))))
    return caminhos
