"""
plot_and_animate.py  — Visualiza saída do CM1 e gera GIF/PNG compartilháveis.

Uso:
    python plot_and_animate.py cm1out.nc

Saídas:
    cm1_animation.gif     — animação completa (envie ao Antigravity)
    cm1_snapshot_T???.png — frames individuais em momentos-chave
    cm1_panel_final.png   — painel 4x do último timestep
"""

import sys
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")          # sem display — funciona no VLab
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import BoundaryNorm, TwoSlopeNorm
import netCDF4 as nc

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("  [aviso] Pillow não encontrado — GIF será gerado via matplotlib")

# ─────────────────────────────────────────────
# Parâmetros do usuário
# ─────────────────────────────────────────────
NCFILE   = sys.argv[1] if len(sys.argv) > 1 else "cm1out.nc"
OUT_GIF  = "cm1_animation.gif"
OUT_FIG  = "cm1_panel_final.png"
DPI      = 110          # resolução dos frames
SKIP     = 1            # usar todos os tempos (2 = um de cada 2)

# Níveis de contorno
LEVELS_W   = np.arange(-20, 21, 2)          # w (m/s)
LEVELS_THP = np.arange(-20, 0.5, 2)         # θ' negativo (pool frio, K)
LEVELS_DBZ = np.arange(10, 75, 5)           # refletividade (dBZ)

CMAP_W   = "RdBu_r"
CMAP_THP = "Blues_r"
CMAP_DBZ = "gist_ncar"

# ─────────────────────────────────────────────
# Ler arquivo NetCDF
# ─────────────────────────────────────────────
print(f"  Lendo: {NCFILE}")
ds = nc.Dataset(NCFILE)

# ─────────────────────────────────────────────
# Coordenadas — detecção robusta de unidades
# ─────────────────────────────────────────────
def get_coord_km(ds, *names):
    """Lê coordenada e converte para km, detectando unidades automaticamente."""
    for n in names:
        if n in ds.variables:
            v   = ds.variables[n]
            arr = v[:]
            # Verificar atributo 'units' primeiro
            units = getattr(v, "units", "").lower()
            if "meter" in units or units == "m":
                arr = arr / 1000.0    # metros → km
                print(f"    {n}: unidade='{units}' → convertido para km "
                      f"(range: {arr.min():.2f} – {arr.max():.2f} km)")
            elif "km" in units or "kilometer" in units:
                print(f"    {n}: unidade='{units}' → já em km "
                      f"(range: {arr.min():.2f} – {arr.max():.2f} km)")
            else:
                # Sem atributo: heurística pelo valor máximo
                if np.max(np.abs(arr)) > 500:
                    arr = arr / 1000.0
                    print(f"    {n}: unidade desconhecida ('{units}') → "
                          f"assumido metros, convertido (range: {arr.min():.2f} – {arr.max():.2f} km)")
                else:
                    print(f"    {n}: unidade desconhecida ('{units}') → "
                          f"assumido km (range: {arr.min():.2f} – {arr.max():.2f} km)")
            return arr
    return None

x = get_coord_km(ds, "xh", "x", "ni")
z = get_coord_km(ds, "z",  "zh", "nk")

def get_var(ds, *names):
    """Lê variável do NetCDF pelo primeiro nome encontrado."""
    for n in names:
        if n in ds.variables:
            return ds.variables[n][:]
    return None

t = get_var(ds, "time", "nt")


# Variáveis 3D (t, z, x) ou (t, nk, ni)
w    = get_var(ds, "winterp", "w")
th   = get_var(ds, "th", "theta")
th0  = get_var(ds, "th0")            # estado base
dbz  = get_var(ds, "dbz")
qr   = get_var(ds, "qr")
qc   = get_var(ds, "qc")
qi   = get_var(ds, "qi")

# θ' = θ - θ0
if th is not None and th0 is not None:
    thp = th - th0[np.newaxis, :, :]
elif th is not None:
    thp = th - th[:, :, :].mean(axis=(0, 2), keepdims=True)
else:
    thp = None

nt = t.shape[0] if t is not None else (w.shape[0] if w is not None else 1)
print(f"  Timesteps: {nt}  |  shape w: {w.shape if w is not None else 'N/A'}")

# ─────────────────────────────────────────────
# Função de plotagem de um frame
# ─────────────────────────────────────────────
def plot_frame(tidx, ax_w, ax_thp, ax_dbz, ax_qr):
    """Plota 4 painéis para o instante tidx."""

    # --- Eixos base ---
    if x is None:
        nx = w.shape[-1] if w is not None else 1
        nz = w.shape[-2] if w is not None else 1
        xg = np.linspace(0, nx * 0.1, nx)
        zg = np.linspace(0, nz * 0.15, nz)
    else:
        xg = x
        zg = z if z is not None else np.arange(w.shape[-2]) * 0.15

    XX, ZZ = np.meshgrid(xg, zg)
    t_min  = (t[tidx] / 60.0) if t is not None else tidx * 5.0

    def _slice(arr):
        """Pega o slice 2D (z, x) do timestep tidx."""
        if arr is None:
            return None
        a = arr[tidx]
        # Se 3D com y: pega y=0
        if a.ndim == 3:
            a = a[:, 0, :]
        return np.squeeze(a)

    w_2d   = _slice(w)
    thp_2d = _slice(thp)
    dbz_2d = _slice(dbz)
    qr_2d  = _slice(qr)

    # ── Painel 1: velocidade vertical w ──────────────────────────────
    if w_2d is not None:
        norm = TwoSlopeNorm(vmin=-20, vcenter=0, vmax=20)
        cf = ax_w.contourf(XX, ZZ, w_2d, levels=LEVELS_W,
                           cmap=CMAP_W, norm=norm, extend="both")
        ax_w.set_title(f"w (m/s) — t={t_min:.0f} min", fontsize=9)
        plt.colorbar(cf, ax=ax_w, fraction=0.03, pad=0.02)

    # ── Painel 2: perturbação θ (pool frio) ──────────────────────────
    if thp_2d is not None:
        cold = np.where(thp_2d < 0, thp_2d, np.nan)
        cf2 = ax_thp.contourf(XX, ZZ, cold, levels=LEVELS_THP,
                              cmap=CMAP_THP, extend="min")
        ax_thp.set_title(f"θ' frio (K) — t={t_min:.0f} min", fontsize=9)
        plt.colorbar(cf2, ax=ax_thp, fraction=0.03, pad=0.02)
        # Contorno positivo (updraft térmico)
        warm = np.where(thp_2d > 0.5, thp_2d, np.nan)
        ax_thp.contour(XX, ZZ, warm,
                       levels=[1, 2, 4, 6], colors="red", linewidths=0.8)

    # ── Painel 3: refletividade dBZ ──────────────────────────────────
    if dbz_2d is not None:
        norm3 = BoundaryNorm(LEVELS_DBZ, ncolors=256)
        cf3 = ax_dbz.contourf(XX, ZZ, np.where(dbz_2d > 10, dbz_2d, np.nan),
                              levels=LEVELS_DBZ, cmap=CMAP_DBZ,
                              norm=norm3, extend="max")
        ax_dbz.set_title(f"dBZ — t={t_min:.0f} min", fontsize=9)
        plt.colorbar(cf3, ax=ax_dbz, fraction=0.03, pad=0.02)

    # ── Painel 4: mixing ratio chuva qr (g/kg) ───────────────────────
    if qr_2d is not None:
        cf4 = ax_qr.contourf(XX, ZZ, qr_2d * 1000.0,
                             levels=np.arange(0.1, 8, 0.5),
                             cmap="Blues", extend="max")
        ax_qr.set_title(f"qr (g/kg) — t={t_min:.0f} min", fontsize=9)
        plt.colorbar(cf4, ax=ax_qr, fraction=0.03, pad=0.02)

    # Labels comuns
    for ax in [ax_w, ax_thp, ax_dbz, ax_qr]:
        ax.set_xlabel("x (km)", fontsize=8)
        ax.set_ylabel("z (km)", fontsize=8)
        ax.set_ylim(0, 12)
        ax.tick_params(labelsize=7)

# ─────────────────────────────────────────────
# Gerar frames
# ─────────────────────────────────────────────
frames_pil = []
frame_files = []

indices = list(range(0, nt, SKIP))
print(f"  Gerando {len(indices)} frames...")

for i, tidx in enumerate(indices):
    fig = plt.figure(figsize=(14, 7), facecolor="#1a1a2e")
    gs  = gridspec.GridSpec(2, 2, hspace=0.38, wspace=0.35,
                            left=0.06, right=0.97, top=0.93, bottom=0.08)
    ax_w   = fig.add_subplot(gs[0, 0])
    ax_thp = fig.add_subplot(gs[0, 1])
    ax_dbz = fig.add_subplot(gs[1, 0])
    ax_qr  = fig.add_subplot(gs[1, 1])

    for ax in [ax_w, ax_thp, ax_dbz, ax_qr]:
        ax.set_facecolor("#0d1117")
        ax.tick_params(colors="white", labelsize=7)
        ax.xaxis.label.set_color("white")
        ax.yaxis.label.set_color("white")
        ax.title.set_color("white")
        for spine in ax.spines.values():
            spine.set_edgecolor("#444")

    t_min = (t[tidx] / 60.0) if t is not None else tidx * 5.0
    fig.suptitle(f"CM1 — Toró Subtropical  |  t = {t_min:.0f} min",
                 color="white", fontsize=12, fontweight="bold")

    plot_frame(tidx, ax_w, ax_thp, ax_dbz, ax_qr)

    fname = f"_frame_{i:04d}.png"
    fig.savefig(fname, dpi=DPI, facecolor=fig.get_facecolor())
    frame_files.append(fname)

    if HAS_PIL:
        frames_pil.append(Image.open(fname).copy())

    plt.close(fig)
    if (i + 1) % 5 == 0:
        print(f"    frame {i+1}/{len(indices)}")

# ─────────────────────────────────────────────
# Salvar GIF
# ─────────────────────────────────────────────
if HAS_PIL and frames_pil:
    print(f"  Salvando GIF: {OUT_GIF}")
    frames_pil[0].save(
        OUT_GIF,
        save_all=True,
        append_images=frames_pil[1:],
        optimize=True,
        duration=400,          # ms por frame
        loop=0
    )
    print(f"  ✓ GIF salvo: {OUT_GIF}")
else:
    print("  [info] PIL não disponível — instale com: pip install Pillow")
    print(f"  Frames salvos como: _frame_XXXX.png")

# ─────────────────────────────────────────────
# Salvar painel final (último timestep)
# ─────────────────────────────────────────────
fig2 = plt.figure(figsize=(14, 7), facecolor="#1a1a2e")
gs2  = gridspec.GridSpec(2, 2, hspace=0.38, wspace=0.35,
                         left=0.06, right=0.97, top=0.93, bottom=0.08)
ax_w2   = fig2.add_subplot(gs2[0, 0])
ax_thp2 = fig2.add_subplot(gs2[0, 1])
ax_dbz2 = fig2.add_subplot(gs2[1, 0])
ax_qr2  = fig2.add_subplot(gs2[1, 1])

for ax in [ax_w2, ax_thp2, ax_dbz2, ax_qr2]:
    ax.set_facecolor("#0d1117")
    ax.tick_params(colors="white", labelsize=7)
    ax.xaxis.label.set_color("white")
    ax.yaxis.label.set_color("white")
    ax.title.set_color("white")
    for spine in ax.spines.values():
        spine.set_edgecolor("#444")

t_final = (t[-1] / 60.0) if t is not None else nt * 5.0
fig2.suptitle(f"CM1 — Toró Subtropical  |  t = {t_final:.0f} min (final)",
              color="white", fontsize=12, fontweight="bold")

plot_frame(nt - 1, ax_w2, ax_thp2, ax_dbz2, ax_qr2)
fig2.savefig(OUT_FIG, dpi=150, facecolor=fig2.get_facecolor())
plt.close(fig2)
print(f"  ✓ Painel final salvo: {OUT_FIG}")

# ─────────────────────────────────────────────
# Limpar frames temporários
# ─────────────────────────────────────────────
for f in frame_files:
    try:
        os.remove(f)
    except OSError:
        pass

ds.close()
print("\n  Pronto! Arquivos gerados:")
if HAS_PIL:
    print(f"    → {OUT_GIF}   (envie ao Antigravity)")
print(f"    → {OUT_FIG}   (painel do instante final)")
