import json
import os
import sys
import matplotlib.pyplot as plt
import numpy as np
 
RESULTS_FILE = "resultados.json"
OUTPUT_DIR   = "graficos"
 
CORES  = {"astar": "#4C9BE8", "greedy": "#E8784C"}
LABELS = {"astar": "A*",      "greedy": "Busca Gulosa"}
 
 
def load_results():
    if not os.path.isfile(RESULTS_FILE):
        print(f"Arquivo '{RESULTS_FILE}' nao encontrado.")
        sys.exit(1)
    with open(RESULTS_FILE, encoding="utf-8") as f:
        return json.load(f)
 
 
def split_by_algo(data):
    by_algo = {}
    for r in data:
        by_algo.setdefault(r["algoritmo"], []).append(r)
    return by_algo
 
 
def save_and_show(fig, filename):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    print(f"  Salvo: {path}")
    plt.show()
    plt.close(fig)
 
 
def plot_barras(by_algo, metrica, ylabel, titulo, filename):
    fig, ax = plt.subplots(figsize=(7, 5))
    algos  = list(by_algo.keys())
    medias = [np.mean([r[metrica] for r in by_algo[a]]) for a in algos]
 
    bars = ax.bar(
        [LABELS[a] for a in algos], medias,
        color=[CORES[a] for a in algos],
        edgecolor="white", width=0.5,
    )
    for bar, media in zip(bars, medias):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() * 1.02,
            f"{media:.2f}",
            ha="center", va="bottom", fontsize=12, fontweight="bold",
        )
 
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(titulo, fontsize=14, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    save_and_show(fig, filename)
 
 
def plot_taxa_sucesso(by_algo):
    fig, ax = plt.subplots(figsize=(7, 5))
    algos = list(by_algo.keys())
    taxas, labels_bar = [], []
 
    for algo in algos:
        subset = by_algo[algo]
        n = len(subset)
        s = sum(1 for r in subset if r["sucesso"])
        taxas.append(100 * s / n)
        labels_bar.append(f"{s}/{n}\n({100*s/n:.1f}%)")
 
    bars = ax.bar(
        [LABELS[a] for a in algos], taxas,
        color=[CORES[a] for a in algos],
        edgecolor="white", width=0.5,
    )
    for bar, lbl in zip(bars, labels_bar):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1,
            lbl,
            ha="center", va="bottom", fontsize=11, fontweight="bold",
        )
 
    ax.set_ylim(0, 115)
    ax.set_ylabel("Taxa de Sucesso (%)", fontsize=12)
    ax.set_title("Taxa de Sucesso", fontsize=14, fontweight="bold")
    ax.axhline(100, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    save_and_show(fig, "1_taxa_sucesso.png")
 
 
def main():
    data    = load_results()
    by_algo = split_by_algo(data)
 
    print(f"\nAlgoritmos: {list(by_algo.keys())}")
    print("Gerando graficos...\n")
 
    plot_taxa_sucesso(by_algo)
 
    plot_barras(by_algo, "custo",          "Custo medio (pontos)", "Custo Medio",          "2_custo.png")
    plot_barras(by_algo, "tempo_s",        "Tempo medio (s)",      "Tempo Medio",          "3_tempo.png")
    plot_barras(by_algo, "nos_expandidos", "Nos expandidos medio", "Nos Expandidos Medio", "4_nos.png")
    plot_barras(by_algo, "passos",         "Passos medios",        "Passos Medios",        "5_passos.png")
 
    print(f"\nGraficos salvos em '{OUTPUT_DIR}/'")
 
 
if __name__ == "__main__":
    main()