# Otimizando-Rota-de-Drones

Projeto de planejamento de rota para drone em grade 3D com restricoes de tempo, bateria, vento, obstaculos fixos, estacoes de recarga e zonas de exclusao temporaria (TNFZ). O nucleo usa `simpleai` (`SearchProblem`) e compara `bfs`, `dfs`, `ucs`, `greedy` e `astar`.

## Visao geral

Fluxo principal do projeto:

1. `[src/environment.py](src/environment.py)`: gera instancias (`UrbanInstance`) com mapa, vento, TNFZ e estacoes.
2. `[src/search_problem.py](src/search_problem.py)`: define estados, acoes, custo e heuristica admissivel.
3. `[src/runners.py](src/runners.py)`: executa os algoritmos e coleta metricas.
4. `[experiments/run_batch.py](experiments/run_batch.py)`: roda lote de instancias e exporta CSV.
5. `[experiments/generate_report.py](experiments/generate_report.py)`: gera relatorio HTML a partir do CSV.

## Requisitos

- Python 3.10 ou superior
- Dependencias em `requirements.txt`

## Instalacao

Na raiz do repositorio:

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Execucao em lote (metricas do relatorio)

Roda 55 instancias (>=50) em quatro fatias (`baseline`, `no_wind`, `no_tnfz`, `low_battery`) e grava metricas em CSV.

```bash
python3 experiments/run_batch.py
```

Saida padrao: `[results/batch_runs.csv](results/batch_runs.csv)`.

Opcoes uteis:

```bash
python3 experiments/run_batch.py --output results/outro.csv --timeout 45
```

`--timeout` define limite de tempo de parede por algoritmo/instancia.

## Relatorio visual (HTML)

Depois de gerar o CSV:

```bash
python3 experiments/generate_report.py
```

Abra `[results/report.html](results/report.html)` no navegador:

- Linux: `xdg-open results/report.html`
- macOS: `open results/report.html`
- Windows (PowerShell): `start results\\report.html`

## Demo pratica 3D comparativa

Para apresentacao visual dos algoritmos no mesmo cenario:

```bash
python3 experiments/demo_compare_3d.py
```

Opcoes:

```bash
python3 experiments/demo_compare_3d.py --seed 7 --timeout 25 --speed 1.2 --slice baseline
```

Controles:

- `SPACE`: pausar/retomar
- `R`: reiniciar
- `+` / `-`: ajustar velocidade
- `ESC`: sair

## Arena legada (Pygame)

Os scripts legados de arena ficam em `[legacy/astas3d.py](legacy/astas3d.py)`, `[legacy/run.py](legacy/run.py)` e `[legacy/plot_results.py](legacy/plot_results.py)`. O launcher simplificado na raiz e `[arena.py](arena.py)`.

## Contexto academico

A eficiencia combina tempo de voo e consumo de energia. As hipoteses de modelagem (grade discreta, tempo discreto, campo de vento por instancia, etc.) devem ser explicitadas no relatorio final.
