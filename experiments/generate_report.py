"""
Gera results/report.html — visão agregada do CSV (taxa de sucesso, tempos médios,
nós visitados) e tabela completa com destaque para falhas.

Uso (na raiz do repositório):
    python experiments/generate_report.py
    python experiments/generate_report.py --input results/outro.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _float(s: str) -> float | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _bool(s: str) -> bool:
    return str(s).strip().lower() in ("true", "1", "yes")


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def aggregate(rows: list[dict[str, str]]):
    """Por algoritmo: sucessos, tempos e nós (média só onde success)."""
    by_algo = defaultdict(lambda: {"ok": 0, "n": 0, "times": [], "nodes": [], "costs": []})
    by_slice = defaultdict(lambda: {"ok": 0, "n": 0})
    for r in rows:
        a = r["algorithm"]
        by_algo[a]["n"] += 1
        if _bool(r["success"]):
            by_algo[a]["ok"] += 1
            t = _float(r["wall_time_sec"])
            if t is not None:
                by_algo[a]["times"].append(t)
            nv = int(r["visited_nodes"] or 0)
            by_algo[a]["nodes"].append(nv)
            pc = _float(str(r.get("path_cost", "")))
            if pc is not None:
                by_algo[a]["costs"].append(pc)
        sl = r.get("experiment_slice", "—")
        by_slice[sl]["n"] += 1
        if _bool(r["success"]):
            by_slice[sl]["ok"] += 1
    return by_algo, by_slice


def _avg(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _bar_svg(labels: list[str], values: list[float], title: str, unit: str) -> str:
    if not values or max(values) <= 0:
        return f"<p class='muted'>Sem dados para «{title}».</p>"
    mx = max(values)
    w, h_bar, gap = 520, 28, 8
    y = 0
    parts = [
        f'<svg class="chart" viewBox="0 0 {w} {len(values) * (h_bar + gap) + 40}" xmlns="http://www.w3.org/2000/svg">',
        f"<text x='0' y='18' class='chart-title'>{title}</text>",
    ]
    y0 = 32
    for i, (lab, val) in enumerate(zip(labels, values)):
        y = y0 + i * (h_bar + gap)
        frac = val / mx
        bw = max(4, int((w - 140) * frac))
        parts.append(
            f'<text x="0" y="{y + 20}" class="lab">{lab}</text>'
            f'<rect x="130" y="{y}" width="{bw}" height="{h_bar}" class="bar" rx="4"/>'
            f'<text x="{138 + bw}" y="{y + 20}" class="val">{val:.4f}{unit}</text>'
        )
    parts.append("</svg>")
    return "\n".join(parts)


def build_html(rows: list[dict[str, str]], by_algo, by_slice) -> str:
    algos = ["bfs", "dfs", "ucs", "greedy", "astar"]
    times = [_avg(by_algo[a]["times"]) for a in algos]
    nodes = [_avg(by_algo[a]["nodes"]) if by_algo[a]["nodes"] else 0 for a in algos]
    success_pct = [
        (100.0 * by_algo[a]["ok"] / by_algo[a]["n"]) if by_algo[a]["n"] else 0 for a in algos
    ]

    slice_rows = "".join(
        f"<tr><td>{sl}</td><td>{d['ok']}/{d['n']}</td>"
        f"<td>{100.0 * d['ok'] / d['n']:.1f}%</td></tr>"
        for sl, d in sorted(by_slice.items())
    )

    table_body = []
    for r in rows:
        ok = _bool(r["success"])
        row_cls = "row-ok" if ok else "row-fail"
        table_body.append(
            f"<tr class='{row_cls}'>"
            f"<td>{r['seed']}</td><td>{r['experiment_slice']}</td><td>{r['algorithm']}</td>"
            f"<td>{'sim' if ok else 'não'}</td>"
            f"<td>{r.get('path_cost', '')}</td><td>{r.get('plan_length', '')}</td>"
            f"<td>{r.get('wall_time_sec', '')}</td><td>{r.get('visited_nodes', '')}</td>"
            f"<td>{r.get('timeout', '')}</td></tr>"
        )

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Resultados — Otimizando Rota de Drones</title>
  <style>
    :root {{
      --bg: #0f1419;
      --card: #1a2332;
      --text: #e7ecf3;
      --muted: #8b9cb3;
      --accent: #3d9cf0;
      --ok: #3ecf8e;
      --fail: #f06b6b;
    }}
    body {{
      font-family: "Segoe UI", system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      margin: 0;
      padding: 24px 32px 48px;
      line-height: 1.5;
    }}
    h1 {{ font-size: 1.75rem; margin-bottom: 0.25rem; }}
    .sub {{ color: var(--muted); margin-bottom: 28px; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 20px;
      margin-bottom: 32px;
    }}
    .card {{
      background: var(--card);
      border-radius: 12px;
      padding: 20px 22px;
      border: 1px solid rgba(255,255,255,.06);
    }}
    .card h2 {{ font-size: 1rem; margin: 0 0 12px; color: var(--accent); }}
    table.summary {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
    table.summary th, table.summary td {{
      text-align: left;
      padding: 8px 10px;
      border-bottom: 1px solid rgba(255,255,255,.08);
    }}
    table.summary th {{ color: var(--muted); font-weight: 600; }}
    .chart {{ width: 100%; max-width: 640px; height: auto; }}
    .chart .lab {{ fill: var(--text); font-size: 13px; }}
    .chart .val {{ fill: var(--muted); font-size: 12px; }}
    .chart .bar {{ fill: var(--accent); }}
    .chart-title {{ fill: var(--muted); font-size: 13px; }}
    .muted {{ color: var(--muted); }}
    .full {{
      overflow-x: auto;
      background: var(--card);
      border-radius: 12px;
      padding: 16px;
      border: 1px solid rgba(255,255,255,.06);
    }}
    table.data {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
    table.data th {{
      position: sticky;
      top: 0;
      background: #243044;
      padding: 10px 8px;
      text-align: left;
    }}
    table.data td {{ padding: 8px; border-bottom: 1px solid rgba(255,255,255,.05); }}
    tr.row-ok td:first-of-type {{ border-left: 3px solid var(--ok); }}
    tr.row-fail td:first-of-type {{ border-left: 3px solid var(--fail); }}
    .hint {{
      margin-top: 24px;
      padding: 14px 18px;
      background: rgba(61, 156, 240, .12);
      border-radius: 8px;
      border: 1px solid rgba(61, 156, 240, .35);
      font-size: 0.9rem;
    }}
  </style>
</head>
<body>
  <h1>Resultados dos algoritmos de busca</h1>
  <p class="sub">Gerado a partir do CSV de experimentos — use no relatório ou na apresentação.</p>

  <div class="grid">
    <div class="card">
      <h2>Taxa de sucesso por algoritmo</h2>
      {_bar_svg(algos, success_pct, "Sucesso (%)", "%")}
    </div>
    <div class="card">
      <h2>Tempo médio de parede (s) — só runs com sucesso</h2>
      {_bar_svg(algos, times, "wall_time_sec", " s")}
    </div>
    <div class="card">
      <h2>Nós visitados (média) — sucesso</h2>
      {_bar_svg(algos, nodes, "visited_nodes", "")}
    </div>
    <div class="card">
      <h2>Sucesso por fatia experimental</h2>
      <table class="summary">
        <thead><tr><th>Fatia</th><th>Sucessos / total</th><th>%</th></tr></thead>
        <tbody>{slice_rows}</tbody>
      </table>
    </div>
  </div>

  <h2 style="font-size:1.1rem;margin-bottom:12px;">Todas as execuções</h2>
  <div class="full">
    <table class="data">
      <thead>
        <tr>
          <th>seed</th><th>fatia</th><th>algoritmo</th><th>sucesso</th>
          <th>custo</th><th>passos</th><th>tempo (s)</th><th>nós</th><th>timeout</th>
        </tr>
      </thead>
      <tbody>{"".join(table_body)}</tbody>
    </table>
  </div>

  <p class="hint">
    <strong>Como abrir:</strong> clique duas vezes em <code>results/report.html</code> no Explorer,
    ou no terminal: <code>start results\\report.html</code> (Windows).
    No VS Code / Cursor: botão direito no ficheiro → <em>Reveal in File Explorer</em>.
  </p>
</body>
</html>"""


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, default=ROOT / "results" / "batch_runs.csv")
    p.add_argument("--output", type=Path, default=ROOT / "results" / "report.html")
    args = p.parse_args()

    if not args.input.is_file():
        print(f"Ficheiro não encontrado: {args.input}", file=sys.stderr)
        sys.exit(1)

    rows = load_rows(args.input)
    by_algo, by_slice = aggregate(rows)
    html = build_html(rows, by_algo, by_slice)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    print(f"Relatório escrito em {args.output}")


if __name__ == "__main__":
    main()
