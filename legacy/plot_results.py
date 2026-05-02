

import json
import os
import sys
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

RESULTS_FILE = "resultados.json"
OUTPUT_DIR   = "graficos"

CORES = {
    "astar":  "#4C9BE8",
    "greedy": "#E8784C",
}
LABELS = {
    "astar":  "A*",
    "greedy": "Busca Gulosa",
}


def load_results():
    if not os.path.isfile(RESULTS_FILE):
        print(f"Arquivo '{RESULTS_FILE}' nao encontrado.")
        print("Execute 'python run_experiments.py' primeiro.")
        sys.exit(1)
    with open(RESULTS_FILE, encoding="utf-8") as f:
        return json.load(f)


def split_by_algo(data):
    by_algo = {}
    for r in data:
        by_algo.setdefault(r["algoritmo"], []).append(r)
    for algo in by_algo:
        by_algo[algo].sort(key=lambda r: r["instancia"])
    return by_algo


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def save_and_show(fig, filename):
    path = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    print(f"  Salvo: {path}")
    plt.show()
    plt.close(fig)


def plot_taxa_sucesso(by_algo):
    fig, ax = plt.subplots(figsize=(7, 5))
    algos = list(by_algo.keys())
    taxas, counts = [], []
    for algo in algos:
        subset = by_algo[algo]
        n = len(subset)
        s = sum(1 for r in subset if r["sucesso"])
        taxas.append(100 * s / n)
        counts.append((s, n))

    bars = ax.bar(
        [LABELS[a] for a in algos], taxas,
        color=[CORES[a] for a in algos],
        edgecolor="white", width=0.5,
    )
    for bar, (s, n), taxa in zip(bars, counts, taxas):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1,
            f"{s}/{n}\n({taxa:.1f}%)",
            ha="center", va="bottom", fontsize=11, fontweight="bold",
        )
    ax.set_ylim(0, 115)
    ax.set_ylabel("Taxa de Sucesso (%)", fontsize=12)
    ax.set_title("Taxa de Sucesso por Algoritmo", fontsize=14, fontweight="bold")
    ax.axhline(100, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    save_and_show(fig, "1_taxa_sucesso.png")


def plot_boxplot(by_algo, metrica, ylabel, titulo, filename):
    fig, ax = plt.subplots(figsize=(8, 5))
    algos = list(by_algo.keys())
    dados, medias = [], []
    for algo in algos:
        vals = [r[metrica] for r in by_algo[algo]]
        dados.append(vals)
        medias.append(np.mean(vals) if vals else 0)

    bp = ax.boxplot(dados, patch_artist=True, widths=0.4,
                    medianprops=dict(color="white", linewidth=2))
    for patch, algo in zip(bp["boxes"], algos):
        patch.set_facecolor(CORES[algo])
        patch.set_alpha(0.8)
    for w in bp["whiskers"]: w.set_color("gray")
    for c in bp["caps"]:     c.set_color("gray")
    for f in bp["fliers"]:   f.set(marker="o", color="gray", alpha=0.4, markersize=4)

    for i, (media, algo) in enumerate(zip(medias, algos), start=1):
        ax.plot(i, media, marker="^", color=CORES[algo], markersize=10, zorder=5,
                label=f"Media {LABELS[algo]}: {media:.1f}")

    ax.set_xticks(range(1, len(algos) + 1))
    ax.set_xticklabels([LABELS[a] for a in algos], fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(titulo, fontsize=14, fontweight="bold")
    ax.legend(fontsize=10, loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    save_and_show(fig, filename)


def plot_linha(by_algo, metrica, ylabel, titulo, filename):
    fig, ax = plt.subplots(figsize=(12, 5))
    for algo, subset in by_algo.items():
        inst   = [r["instancia"] for r in subset]
        vals   = [r[metrica] for r in subset]
        ax.plot(inst, vals, color=CORES[algo], label=LABELS[algo],
                linewidth=1.2, alpha=0.85)
        if len(vals) >= 10:
            mm  = np.convolve(vals, np.ones(10) / 10, mode="valid")
            x_m = inst[9:]
            ax.plot(x_m, mm, color=CORES[algo], linewidth=2.5,
                    linestyle="--", alpha=0.9)

    handles = [mpatches.Patch(color=CORES[a], label=LABELS[a]) for a in by_algo]
    ax.legend(handles=handles, fontsize=11)
    ax.set_xlabel("Instancia", fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(
        titulo + "\n(solida = valor bruto  |  tracejada = media movel 10 inst.)",
        fontsize=13, fontweight="bold",
    )
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    save_and_show(fig, filename)


def plot_tabela_resumo(by_algo):
    fig, ax = plt.subplots(figsize=(11, 3.5))
    ax.axis("off")
    algos = list(by_algo.keys())
    colunas = ["Algoritmo", "Sucesso", "Custo medio",
               "Tempo medio (s)", "Nos medios", "Passos medios"]
    rows = []
    for algo in algos:
        subset  = by_algo[algo]
        n       = len(subset)
        s       = sum(1 for r in subset if r["sucesso"])
        c_med   = np.mean([r["custo"] for r in subset])
        t_med   = np.mean([r["tempo_s"] for r in subset])
        n_med   = np.mean([r["nos_expandidos"] for r in subset])
        p_med   = np.mean([r["passos"] for r in subset])
        rows.append([
            LABELS[algo],
            f"{s}/{n} ({100*s/n:.0f}%)",
            f"{c_med:.1f}",
            f"{t_med:.4f}",
            f"{n_med:.0f}",
            f"{p_med:.0f}",
        ])

    table = ax.table(cellText=rows, colLabels=colunas,
                     cellLoc="center", loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 2.2)

    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor("#2E4057")
            cell.set_text_props(color="white", fontweight="bold")
        elif row == 1 and len(algos) > 0:
            cell.set_facecolor(CORES.get(algos[0], "#FFFFFF") + "33")
        elif row == 2 and len(algos) > 1:
            cell.set_facecolor(CORES.get(algos[1], "#FFFFFF") + "33")
        cell.set_edgecolor("white")

    ax.set_title("Resumo Comparativo  --  A* vs Busca Gulosa",
                 fontsize=14, fontweight="bold", pad=20)
    fig.tight_layout()
    save_and_show(fig, "9_tabela_resumo.png")


def main():
    ensure_output_dir()
    data    = load_results()
    by_algo = split_by_algo(data)

    print(f"\nAlgoritmos: {list(by_algo.keys())}")
    for algo, subset in by_algo.items():
        print(f"  {LABELS.get(algo, algo)}: {len(subset)} instancias")
    print("\nGerando graficos...\n")

    plot_taxa_sucesso(by_algo)
    plot_boxplot(by_algo, "custo",          "Custo (pontos)",
                 "Custo do Caminho por Algoritmo",         "2_custo_boxplot.png")
    plot_boxplot(by_algo, "tempo_s",        "Tempo (s)",
                 "Tempo de Execucao por Algoritmo",        "3_tempo_boxplot.png")
    plot_boxplot(by_algo, "nos_expandidos", "Nos Expandidos",
                 "Nos Expandidos por Algoritmo",           "4_nos_boxplot.png")
    plot_boxplot(by_algo, "passos",         "Passos",
                 "Passos Totais por Algoritmo",            "5_passos_boxplot.png")
    plot_linha(by_algo, "custo",          "Custo (pontos)",  "Custo por Instancia",         "6_custo_linha.png")
    plot_linha(by_algo, "tempo_s",        "Tempo (s)",       "Tempo por Instancia",         "7_tempo_linha.png")
    plot_linha(by_algo, "nos_expandidos", "Nos Expandidos",  "Nos Expandidos por Instancia","8_nos_linha.png")
    plot_tabela_resumo(by_algo)

    print(f"\nTodos os graficos salvos em '{OUTPUT_DIR}/'")


if __name__ == "__main__":
    main()