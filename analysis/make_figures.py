#!/usr/bin/env python3
"""
make_figures.py — Figuras 1–5 em português para o artigo InfraCidades 2026.
Lê os CSVs de data/ e grava PNGs em outputs/figures/ (300 dpi).
Execução a partir da raiz do repositório: python analysis/make_figures.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "outputs" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

ORDER = ["no_protection", "weak_protection", "moderate_protection",
         "strong_protection", "maximum_protection"]
LABELS = ["Sem proteção", "Proteção fraca", "Proteção moderada",
          "Proteção forte", "Proteção máxima"]
COR = {"no_protection": "#d62728", "weak_protection": "#ff7f0e",
       "moderate_protection": "#bcbd22", "strong_protection": "#2ca02c",
       "maximum_protection": "#1f77b4"}

res = pd.read_csv(DATA / "sustainability_scores_all_reps.csv")
ts = pd.read_csv(DATA / "timeseries_all_reps.csv")
rob = pd.read_csv(DATA / "robustness_regimes.csv")
res["ord"] = res["policy_scenario"].map({k: i for i, k in enumerate(ORDER)})
res = res.sort_values("ord")

FONT = {"fontweight": "bold"}

# ---------------------------------------------------------------------------
# Figura 1 — boxplots de sustentabilidade por nível de proteção
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(1, 3, figsize=(16, 5))
for ax, (col, tit) in zip(axes, [
        ("overall_sustainability", "Sustentabilidade geral"),
        ("social_sustainability", "Sustentabilidade social"),
        ("economic_sustainability", "Sustentabilidade econômica")]):
    data = [res.loc[res["policy_scenario"] == k, col] for k in ORDER]
    bp = ax.boxplot(data, labels=[l.replace(" ", "\n") for l in LABELS],
                    patch_artist=True,
                    medianprops=dict(color="black", linewidth=1.5),
                    flierprops=dict(markersize=3))
    for patch, k in zip(bp["boxes"], ORDER):
        patch.set_facecolor(COR[k])
        patch.set_alpha(0.75)
    ax.set_title(tit, fontsize=12, **FONT)
    ax.set_ylabel("Pontuação (0–100)")
    ax.grid(axis="y", alpha=0.3)
    for i, k in enumerate(ORDER):
        m = res.loc[res["policy_scenario"] == k, col].mean()
        ax.scatter(i + 1, m, marker="D", color="white",
                   edgecolor="black", s=45, zorder=5)
fig.suptitle("Sustentabilidade da agricultura urbana por nível de proteção "
             "institucional\n(médias de 30 replicações, horizonte de 20 anos — "
             "losangos brancos = médias)", fontsize=13, **FONT)
plt.tight_layout()
plt.savefig(OUT / "fig1_sustentabilidade_boxplots.png", dpi=300,
            bbox_inches="tight")
plt.close(fig)

# ---------------------------------------------------------------------------
# Figura 2 — dose-resposta
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
for k, lab in zip(ORDER, LABELS):
    d = res[res["policy_scenario"] == k]
    axes[0].scatter(d["protection_index"], d["final_farmers_pct"], s=18,
                    alpha=0.55, color=COR[k], label=lab)
    axes[1].scatter(d["protection_index"], d["land_appreciation_pct"], s=18,
                    alpha=0.55, color=COR[k], label=lab)
gm = res.groupby("policy_scenario").agg(
    pi=("protection_index", "mean"), ret=("final_farmers_pct", "mean"),
    apr=("land_appreciation_pct", "mean")).reindex(ORDER)
xs = np.linspace(0, 0.9, 50)
axes[0].plot(xs, np.polyval(np.polyfit(gm["pi"], gm["ret"], 1), xs), "k--",
             alpha=0.6)
axes[1].plot(xs, np.exp(np.polyval(
    np.polyfit(gm["pi"], np.log(gm["apr"]), 1), xs)), "k--", alpha=0.6)
r1 = np.corrcoef(gm["pi"], gm["ret"])[0, 1]
axes[0].set_title(f"Retenção de agricultores (r = {r1:.2f})", **FONT)
axes[0].set_ylabel("Agricultores remanescentes (%)")
axes[1].set_title("Apreciação fundiária acumulada (log)", **FONT)
axes[1].set_ylabel("Apreciação em 20 anos (%)")
for ax in axes:
    ax.set_xlabel("Índice de proteção (0–1)")
    ax.grid(alpha=0.3)
axes[1].set_yscale("log")
axes[1].legend(fontsize=9, framealpha=0.9)
fig.suptitle("Relação dose–resposta entre proteção institucional e "
             "persistência do sistema", fontsize=13, **FONT)
plt.tight_layout()
plt.savefig(OUT / "fig2_dose_resposta.png", dpi=300, bbox_inches="tight")
plt.close(fig)

# ---------------------------------------------------------------------------
# Figura 3 — equidade × eficiência
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7.5, 6.5))
for k, lab in zip(ORDER, LABELS):
    d = res[res["policy_scenario"] == k]
    ax.scatter(d["social_sustainability"], d["economic_sustainability"],
               s=22, alpha=0.5, color=COR[k], label=lab)
    ax.scatter(d["social_sustainability"].mean(),
               d["economic_sustainability"].mean(), marker="*", s=350,
               color=COR[k], edgecolor="black", zorder=5)
lims = [10, 95]
ax.plot(lims, lims, "k--", alpha=0.4, label="Equilíbrio perfeito")
r = np.corrcoef(res["social_sustainability"],
                res["economic_sustainability"])[0, 1]
ax.set_xlabel("Sustentabilidade social (equidade)")
ax.set_ylabel("Sustentabilidade econômica (eficiência)")
ax.set_title(f"Equidade e eficiência caminham juntas (r = {r:.3f})\n"
             "estrelas = médias por cenário; 30 replicações", **FONT)
ax.legend(fontsize=9, loc="lower right")
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(OUT / "fig3_equidade_eficiencia.png", dpi=300, bbox_inches="tight")
plt.close(fig)

# ---------------------------------------------------------------------------
# Figura 4 — trajetórias de retenção (falha retardada)
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(9, 5.5))
for k, lab in zip(ORDER, LABELS):
    d = ts[ts["policy_scenario"] == k]
    traj = d.groupby("month")["active_farmers"].mean() / 50 * 100
    ax.plot(traj.index / 12, traj.values, color=COR[k], label=lab, linewidth=2)
ax.set_xlabel("Anos")
ax.set_ylabel("Agricultores ativos (% do inicial)")
ax.set_title("Trajetórias de retenção ao longo de 20 anos — avaliações de "
             "curto prazo\n(≤ 5 anos) não capturam o colapso tardio sob "
             "proteção fraca", **FONT)
ax.legend(fontsize=9)
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(OUT / "fig4_trajetorias_retencao.png", dpi=300,
            bbox_inches="tight")
plt.close(fig)

# ---------------------------------------------------------------------------
# Figura 5 — robustez a dois regimes de sucesso inicial
# ---------------------------------------------------------------------------
x = np.arange(len(ORDER))
w = 0.38
fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
summ = rob.groupby(["regime_abm1", "policy_scenario"]).agg(
    ret=("final_farmers_pct", "mean"),
    apr=("land_appreciation_pct", "mean")).reset_index()
for i, (reg, cor, hatch) in enumerate([("MODERATE", "#1f77b4", None),
                                       ("HIGH", "#d62728", "//")]):
    sub = summ[summ["regime_abm1"] == reg].set_index("policy_scenario")
    v_ret = [sub.loc[k, "ret"] for k in ORDER]
    v_apr = [sub.loc[k, "apr"] for k in ORDER]
    b = axes[0].bar(x + (i - 0.5) * w, v_ret, w, label=f"Regime {reg.lower()}",
                    color=cor, edgecolor="black", linewidth=0.6, hatch=hatch,
                    alpha=0.9)
    axes[0].bar_label(b, fmt="%.0f", fontsize=9, padding=2)
    b = axes[1].bar(x + (i - 0.5) * w, v_apr, w, label=f"Regime {reg.lower()}",
                    color=cor, edgecolor="black", linewidth=0.6, hatch=hatch,
                    alpha=0.9)
    axes[1].bar_label(b, fmt="%.0f", fontsize=8, padding=2, rotation=90)
for ax, tit in zip(axes, ["(a) Retenção de agricultores\ngradiente de "
                          "proteção invariante ao sucesso inicial",
                          "(b) Apreciação fundiária\nsucesso inicial amplifica "
                          "a pressão especulativa"]):
    ax.set_xticks(x)
    ax.set_xticklabels([l.replace(" ", "\n") for l in LABELS], fontsize=9)
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    ax.set_title(tit, **FONT, fontsize=11)
axes[0].set_ylabel("Agricultores remanescentes (%)")
axes[1].set_ylabel("Apreciação acumulada em 20 anos (%)")
axes[1].set_yscale("log")
fig.suptitle("Robustez do gradiente de proteção a duas condições iniciais de "
             "sucesso (ABM1):\nmoderado (participação de mercado 18%) vs. alto "
             "(32%) — 30 replicações por cenário", fontsize=12, **FONT)
plt.tight_layout()
plt.savefig(OUT / "fig5_robustez_regimes.png", dpi=300, bbox_inches="tight")
plt.close(fig)

print(f"Figuras salvas em {OUT}")
