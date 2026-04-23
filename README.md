# Otimizando-Rota-de-Drones

Planejamento de rota para um drone de entregas em grid 3D com **tempo**, **bateria**, **vento**, **obstáculos fixos**, **estações de recarga** e **zonas de exclusão temporária (TNFZ)**. O núcleo do trabalho usa a biblioteca **simpleai** (`SearchProblem`) e compara **busca em largura**, **profundidade**, **custo uniforme**, **gulosa** e **A\***.

## Ideia geral (por onde começar)

O projeto faz **uma coisa só**, em cadeia:

1. **`environment.py`** — inventa um “mundo”: grelha 3D, parede onde não podes voar, vento que encarece certos movimentos, zonas proibidas só durante alguns instantes, estações onde podes recarregar bateria, ponto de partida e chegada.
2. **`search_problem.py`** — diz ao **simpleai** o que é um **estado** (onde estás, quanta bateria tens, que “instante” do relógio é), que **ações** existem (andar, esperar, recarregar), quanto **custa** cada passo e quando chegaste ao **objetivo**.
3. **`runners.py`** — chama os cinco algoritmos do simpleai e regista tempo e nós visitados.
4. **`run_batch.py`** — repete isso muitas vezes e grava o **CSV**.
5. **`generate_report.py`** (opcional) — transforma o CSV numa **página HTML** mais fácil de ler.

**Estado em linguagem simples:** “Estou na célula (x,y,z), com esta bateria, neste instante t do simulador.” O tempo `t` serve para as zonas temporárias: o mesmo sítio pode ser permitido no instante 2 e proibido no instante 5.

**Se o objetivo for só correr e ver resultados:** instala dependências, depois `python experiments/run_batch.py` e, se quiseres gráficos, `python experiments/generate_report.py`. O código “difícil” está quase todo em `search_problem.py`; o resto é repetição e relatório.

## Requisitos

- Python 3.10+ recomendado

## Instalação

Na raiz do repositório:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Experimento em lote (métricas para o relatório)

Gera **55 instâncias** (≥50 exigidas) com sementes fixas e quatro fatias (`baseline`, `no_wind`, `no_tnfz`, `low_battery`). Para cada instância roda os cinco algoritmos e grava um CSV com sucesso, custo do caminho, comprimento do plano, tempo de parede, nós visitados (contador do `BaseViewer` do simpleai), tamanho máximo da fringe e iterações.

```powershell
python experiments/run_batch.py
```

Saída padrão: [`results/batch_runs.csv`](results/batch_runs.csv).

### Ver resultados de forma visual

Depois de gerar o CSV, cria um **relatório HTML** com gráficos de barras (taxa de sucesso, tempo médio, nós visitados) e tabela completa com linhas de sucesso/falha destacadas:

```powershell
python experiments/generate_report.py
```

Abre [`results/report.html`](results/report.html) no navegador (duplo clique no ficheiro ou `start results\report.html` no PowerShell). Serve para apresentação oral e para copiar números para o PDF.

Opções:

```powershell
python experiments/run_batch.py --output results/outro.csv --timeout 45
```

O `--timeout` é o limite de **parede** em segundos por algoritmo; se estourar, a linha correspondente marca `timeout=true` (o thread do simpleai pode continuar em segundo plano até terminar).

## Código principal

| Caminho | Função |
|--------|--------|
| [`src/environment.py`](src/environment.py) | Geração de instâncias (`UrbanInstance`, TNFZ, vento, estações). |
| [`src/search_problem.py`](src/search_problem.py) | `DroneUrbanSearchProblem` — estado `(x, y, z, battery, t)`, ações mover/esperar/recarregar, custo tempo+energia, heurística admissível (Manhattan × custo mínimo de movimento). |
| [`src/runners.py`](src/runners.py) | Execução dos algoritmos simpleai com `graph_search=True` e coleta de métricas. |
| [`experiments/run_batch.py`](experiments/run_batch.py) | Script de lote para o CSV. |
| [`experiments/generate_report.py`](experiments/generate_report.py) | Gera `results/report.html` a partir do CSV. |

## Legado (Pygame)

A demo visual antiga com A* manual (`heapq`) foi movida para [`legacy/simple_base_Astar.py`](legacy/simple_base_Astar.py). Ela **não** faz parte do núcleo simpleai da disciplina; exige `pip install pygame` para executar.

## Contexto do problema (enunciado)

A "eficiência" combina tempo de voo e consumo de energia; o ambiente inclui mapa 3D, vento, zonas temporariamente restritas, estações de recarga e obstáculos fixos. As simplificações e hipóteses usadas na implementação devem ser descritas no relatório (grid pequeno, tempo discretizado, vento constante por instância, etc.).
