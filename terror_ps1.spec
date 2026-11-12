# -*- mode: python ; coding: utf-8 -*-
"""
Receita do executavel:  python -m PyInstaller terror_ps1.spec

Sai em dist/TerrorPS1/ (TerrorPS1.exe e a pasta _internal ao lado). Leva
`terror_ps1/data/` no mesmo caminho, porque `DADOS` e relativo ao proprio modulo. `onedir`, nao `onefile`:
o Controle Inteligente de Aplicativos barra o onefile (ver karmabound.spec).
O moderngl acha o contexto OpenGL pelo pacote `glcontext`, importado por nome.
"""
from pathlib import Path

import ouroboros
from PyInstaller.utils.hooks import collect_submodules

RAIZ = Path(SPECPATH).resolve()
ENGINE = Path(ouroboros.__file__).resolve().parent.parent  # instalada em modo editavel: o PyInstaller nao segue o ponteiro

datas = [
    (str(RAIZ / "terror_ps1" / "data"), "terror_ps1/data"),
]
icone = RAIZ / "terror_ps1" / "data" / "icone.ico"

analysis = Analysis(
    [str(RAIZ / "terror_ps1" / "__main__.py")],
    pathex=[str(RAIZ), str(ENGINE)],
    binaries=[],
    datas=datas,
    hiddenimports=[n for n in collect_submodules("ouroboros") if not n.startswith("ouroboros.rhythm.offline")]
    + collect_submodules("terror_ps1")
    + collect_submodules("glcontext") + ["moderngl"],
    excludes=["tkinter", "unittest", "pytest", "numpy.testing", "pygame.tests",
              "scipy", "matplotlib", "PIL", "ouroboros.rhythm.offline"],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(pyz, analysis.scripts, [], exclude_binaries=True, name="TerrorPS1", debug=False,
          strip=False, upx=False, console=False, icon=str(icone) if icone.is_file() else None)
collected = COLLECT(exe, analysis.binaries, analysis.datas, strip=False, upx=False, name="TerrorPS1")
