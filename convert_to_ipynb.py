import nbformat as nbf
import re

nb = nbf.v4.new_notebook()
cells = []

cells.append(nbf.v4.new_markdown_cell("# LH Nautical Data Challenge - Pipeline Completo\n\nEste Notebook contém toda a arquitetura de dados (EDA, Modelagem, Análises, Previsão de Demanda e Relatórios) consolidada para execução no Google Colab.\n\n**Pré-requisito:**\nVocê deve fazer o upload da pasta `1-lh_nautical_csv` (ou seu conteúdo .zip) para o ambiente do Colab antes de rodar."))

cells.append(nbf.v4.new_code_cell("""# Preparação do Ambiente no Colab
!pip install -q statsmodels pandas plotly pytest

import os
BASE_DIR = '.'
os.makedirs(os.path.join(BASE_DIR, 'processed'), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'outputs', 'reports'), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'outputs', 'figures'), exist_ok=True)

# Caso tenha subido o ZIP com os CSVs brutos, descomente e rode a linha abaixo:
# !unzip -q -o 1-lh_nautical_csv.zip -d 1-lh_nautical_csv
"""))

scripts = [
    "01_eda.py",
    "02_tratamento_modelagem.py",
    "03_analise_vendas_clientes.py",
    "04_previsao_recomendacao.py",
    "07_analise_fase2.py",
    "05_dashboard.py",
]

for s in scripts:
    with open(s, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Substitui o diretório absoluto por relativo '.' (compatível com Colab/Linux)
    content = re.sub(r'BASE_DIR\s*=\s*r"C:\\Users\\[^"]+"', "BASE_DIR = '.'", content)
    
    cells.append(nbf.v4.new_markdown_cell(f"## Etapa: `{s}`"))
    cells.append(nbf.v4.new_code_cell(content))

# Adiciona célula final de instrução
cells.append(nbf.v4.new_markdown_cell("## Finalizado!\n\nApós rodar todas as células, os dados limpos estarão na pasta `processed/`, os resultados em `outputs/reports/` e o HTML interativo em `outputs/dashboard_lh_nautical.html`."))

nb['cells'] = cells

with open('LH_Nautical_Colab.ipynb', 'w', encoding='utf-8') as f:
    nbf.write(nb, f)

print("Notebook LH_Nautical_Colab.ipynb criado com sucesso!")
