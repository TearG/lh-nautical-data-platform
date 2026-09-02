"""
=======================================================================
run_all.py - Orquestrador Local - LH Nautical Data Pipeline
=======================================================================
Executa o pipeline completo com DAG de dependencias, retry automatico
e verificacao de freshness dos outputs.

Uso:
  python run_all.py                  # Pipeline completo
  python run_all.py --skip-fresh     # Pula etapas cujos outputs sao recentes
  python run_all.py --only 02        # Executa apenas o script 02
  python run_all.py --only 03 04     # Executa os scripts 03 e 04
  python run_all.py --no-tests       # Pula a suite de testes ao final
  python run_all.py --help           # Lista todas as opcoes
=======================================================================
"""

import argparse
import subprocess
import sys
import os
import time
import logging
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuracao de logging  (terminal + arquivo)
# ---------------------------------------------------------------------------
BASE_DIR   = Path(__file__).parent
LOG_DIR    = BASE_DIR / "outputs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE   = LOG_DIR / "pipeline_run.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(LOG_FILE), encoding="utf-8"),
    ],
)
log = logging.getLogger("pipeline")

# ---------------------------------------------------------------------------
# Definicao do DAG
# ---------------------------------------------------------------------------
PROC   = BASE_DIR / "processed"
REPS   = BASE_DIR / "outputs" / "reports"
OUT    = BASE_DIR / "outputs"
BRONZE = BASE_DIR / "1-lh_nautical_csv"


@dataclass
class Step:
    """Representa uma etapa do pipeline."""
    key: str
    script: str
    desc: str
    inputs: list = field(default_factory=list)
    outputs: list = field(default_factory=list)
    retries: int = 1


STEPS = [
    Step(
        key="01", script="01_eda.py",
        desc="EDA e Qualidade dos Dados",
        inputs=[str(BRONZE / "orders.csv"), str(BRONZE / "order_items.csv")],
        outputs=[str(REPS / "01_qualidade_dados.csv")],
    ),
    Step(
        key="02", script="02_tratamento_modelagem.py",
        desc="Tratamento e Modelagem (Silver + DuckDB)",
        inputs=[str(BRONZE / "orders.csv"), str(BRONZE / "order_items.csv")],
        outputs=[
            str(PROC / "fato_vendas.csv"),
            str(PROC / "fato_payments.csv"),
            str(PROC / "fato_returns.csv"),
            str(PROC / "fato_stock.csv"),
            str(PROC / "dim_customers.csv"),
            str(PROC / "dim_products.csv"),
        ],
    ),
    Step(
        key="03", script="03_analise_vendas_clientes.py",
        desc="Analise de Vendas e Clientes",
        inputs=[str(PROC / "fato_vendas.csv"), str(PROC / "fato_returns.csv")],
        outputs=[
            str(REPS / "03a_vendas_por_ano.csv"),
            str(REPS / "03e_clv_clientes.csv"),
        ],
    ),
    Step(
        key="04", script="04_previsao_recomendacao.py",
        desc="Previsao (Holt-Winters) + Recomendacao (SVD) + RFM",
        inputs=[str(PROC / "fato_vendas.csv")],
        outputs=[
            str(REPS / "04b_segmentacao_rfm.csv"),
            str(REPS / "04c_recomendacoes_por_cliente.csv"),
        ],
    ),
    Step(
        key="06", script="scripts/06_investigacao_veracidade.py",
        desc="Investigacao de Veracidade (Auditoria Fiscal)",
        inputs=[str(PROC / "fato_vendas.csv"), str(PROC / "fato_fiscal.csv")],
        outputs=[],
    ),
    Step(
        key="07", script="07_analise_fase2.py",
        desc="Analise Fase 2 (RH, Supply Chain, Geolocalizacao)",
        inputs=[str(PROC / "fato_compras.csv"), str(PROC / "dim_employees.csv")],
        outputs=[],
    ),
    Step(
        key="05", script="05_dashboard.py",
        desc="Geracao do Dashboard HTML",
        inputs=[
            str(PROC / "fato_vendas.csv"),
            str(REPS / "03a_vendas_por_ano.csv"),
            str(REPS / "04b_segmentacao_rfm.csv"),
        ],
        outputs=[str(OUT / "dashboard_lh_nautical.html")],
    ),
]

STEP_INDEX = {s.key: s for s in STEPS}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_fresh(step):
    """
    Retorna True se TODOS os outputs existem e sao mais recentes
    que TODOS os inputs. Etapas sem outputs nunca sao consideradas frescas.
    """
    if not step.outputs:
        return False
    output_paths = [Path(p) for p in step.outputs]
    if not all(p.exists() for p in output_paths):
        return False
    if not step.inputs:
        return True
    oldest_output = min(p.stat().st_mtime for p in output_paths)
    input_paths   = [Path(p) for p in step.inputs if Path(p).exists()]
    if not input_paths:
        return True
    newest_input = max(p.stat().st_mtime for p in input_paths)
    return oldest_output >= newest_input


def _run_step(step):
    """Executa um step e retorna (sucesso, tempo_segundos)."""
    script_path = BASE_DIR / step.script
    t0 = time.time()
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=False,
    )
    elapsed = time.time() - t0
    return result.returncode == 0, elapsed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="LH Nautical - Orquestrador de Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python run_all.py                   Pipeline completo
  python run_all.py --skip-fresh      Pula etapas com outputs atualizados
  python run_all.py --only 02         Roda apenas o script 02
  python run_all.py --only 03 04      Roda os scripts 03 e 04
  python run_all.py --no-tests        Pula o pytest ao final
        """,
    )
    parser.add_argument(
        "--skip-fresh",
        action="store_true",
        help="Pula etapas cujos outputs ja existem e sao mais recentes que os inputs",
    )
    parser.add_argument(
        "--only",
        nargs="+",
        metavar="KEY",
        help="Executa apenas as etapas com as chaves informadas (ex: --only 02 03)",
    )
    parser.add_argument(
        "--no-tests",
        action="store_true",
        help="Nao executa a suite de testes (pytest) ao final do pipeline",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args  = parse_args()
    steps = list(STEPS)

    if args.only:
        invalidas = [k for k in args.only if k not in STEP_INDEX]
        if invalidas:
            log.error("Chaves invalidas: %s. Chaves validas: %s",
                      invalidas, list(STEP_INDEX.keys()))
            sys.exit(1)
        steps = [STEP_INDEX[k] for k in args.only]

    sep = "=" * 65
    log.info(sep)
    log.info("  LH Nautical - Pipeline de Dados")
    log.info("  Inicio: %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    log.info("  Log:    %s", LOG_FILE)
    log.info(sep)

    resultados = []

    for step in steps:
        log.info("")
        log.info("  [%s] %s", step.key, step.desc)

        if args.skip_fresh and _is_fresh(step):
            log.info("  -> PULADO (outputs mais recentes que inputs)")
            resultados.append((step, "skipped", 0.0))
            continue

        sucesso = False
        elapsed = 0.0
        for attempt in range(1, step.retries + 2):
            if attempt > 1:
                log.warning("  -> Tentativa %d/%d...", attempt, step.retries + 1)
            sucesso, elapsed = _run_step(step)
            if sucesso:
                break

        icon = "[OK]  " if sucesso else "[ERRO]"
        log.info("  %s Concluido em %.1fs", icon, elapsed)
        resultados.append((step, "ok" if sucesso else "fail", elapsed))

    # Suite de testes Pytest
    if not args.no_tests and not args.only:
        log.info("")
        log.info(sep)
        log.info("  Executando suite de testes (pytest)...")
        t0 = time.time()
        r  = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short"],
            capture_output=False,
            cwd=str(BASE_DIR),
        )
        elapsed_tests = time.time() - t0
        icon = "[OK]  " if r.returncode == 0 else "[ERRO]"
        log.info("  %s Testes concluidos em %.1fs", icon, elapsed_tests)

    # Sumario final
    log.info("")
    log.info(sep)
    log.info("  RESULTADO FINAL")
    log.info(sep)
    total_tempo = sum(t for _, _, t in resultados)
    falhas  = [s for s, st, _ in resultados if st == "fail"]
    pulados = [s for s, st, _ in resultados if st == "skipped"]

    for step, status, tempo in resultados:
        icon = {"ok": "[OK] ", "fail": "[ERR]", "skipped": "[SKP]"}.get(status, "[?]")
        log.info("  %s [%s] %-52s %.1fs", icon, step.key, step.desc, tempo)

    log.info("")
    log.info("  Tempo total do pipeline: %.1fs", total_tempo)

    if pulados:
        log.info("  Etapas puladas (fresh): %s", [s.key for s in pulados])

    if not falhas:
        log.info("  [SUCESSO] Pipeline concluido sem erros!")
        dashboard = BASE_DIR / "outputs" / "dashboard_lh_nautical.html"
        if dashboard.exists():
            log.info("  Dashboard: %s", dashboard)
    else:
        log.error("  [ATENCAO] %d etapa(s) com ERRO: %s",
                  len(falhas), [s.key for s in falhas])
        sys.exit(1)

    log.info(sep)


if __name__ == "__main__":
    main()
