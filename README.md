# Agricultura urbana como infraestrutura verde e social: persistência, deslocamento e bens comuns em São Paulo

Material de reprodução do artigo submetido ao **InfraCidades 2026** (FGV EAESP / SP Parcerias).
Contém o modelo baseado em agentes (ABM), os protocolos experimentais
com replicações determinísticas, as análises estatísticas em R e as figuras em português.

## Estrutura do repositório

```
aup_commons_infracidades/
├── README.md                        # este arquivo
├── LICENSE                          
├── CITATION.cff                     # metadados de citação
├── model/
│   ├── abm_v20_colab.py            # ABM — mecânica autoritativa (v2.0, set/2026)
│   └── run_abm_protocols.py        # protocolos A/B/C + robustez de regimes + CSVs
├── analysis/
│   ├── 01_statistical_tests_protocol_A.R   # KW, ε², post-hoc Holm, rank-biserial
│   ├── 02_statistical_tests_protocol_B.R   # fatorial: efeitos principais + interação
│   ├── 03_convergence_and_robustness.R     # convergência de replicações + regimes
│   └── make_figures.py                     # figuras 1–5 em português
├── data/                                   # dados brutos das simulações (CSV)
│   ├── sustainability_scores_all_reps.csv  # protocolo A: 150 runs
│   ├── timeseries_all_reps.csv             # séries mensais (protocolo A)
│   ├── factorial_results.csv               # protocolo B: 300 runs
│   ├── robustness_regimes.csv              # robustez: 300 runs (2 regimes)
│   └── convergence_check.csv               # protocolo C
└── outputs/
    ├── figures/                     
    └── tables/                      # tabelas estatísticas (CSVs gerados pelos scripts R)
```

## Reprodução

**Ambiente:** Python 3.11+ (numpy, pandas, matplotlib) e R ≥ 4.0 (somente base R — sem
dependências externas). Execução a partir da raiz do repositório:

```bash
# 1. Regenera os dados (≈ 2–5 min em máquina comum; 750 simulações de 240 meses)
python model/run_abm_protocols.py

# 2. Análises estatísticas (geram outputs/tables/*.csv)
Rscript analysis/01_statistical_tests_protocol_A.R
Rscript analysis/02_statistical_tests_protocol_B.R
Rscript analysis/03_convergence_and_robustness.R

# 3. Figuras em português (regenera outputs/figures/*.png)
python analysis/make_figures.py
```

Os CSVs em `data/` são os dados reportados no artigo; os scripts R
reproduzem as estatísticas do manuscrito a partir deles sem necessidade de re-simular.

## Notas metodológicas

- **Replicações determinísticas:** cada execução usa semente derivada de
  `CRC32(regime, política, réplica)` — reproduzível entre ambientes computacionais.
- **Otimização vetorial:** `FastModel` (em `run_abm_protocols.py`) pré-computa as
  matrizes de distância espacial; equivalente à versão em laços com divergência
  insignificante em ponto flutuante (< 0,5% relativo na apreciação; sem efeito sobre
  deslocamentos e retenção).
- **Condição primária:** regime MODERATE do ABM1; regime HIGH como análise de
  robustez (seção 4.2 do artigo).

## Como citar

ROSSI, T. J. A.; DE CARVALHO, A. M.; SARTI, F. M. Agricultura urbana como
infraestrutura verde e social: persistência, deslocamento e bens comuns em São
Paulo. InfraCidades 2026, São Paulo, 2026. Código e dados: [URL do repositório].
