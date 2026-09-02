import os
import pandas as pd
import glob
import json

csv_dir = r"C:\Users\vanes\source\repos\nautical\1-lh_nautical_csv"
output_file = r"C:\Users\vanes\source\repos\nautical\schema_info.json"

all_files = glob.glob(os.path.join(csv_dir, "*.csv"))

schema_info = {}

print(f"Encontrados {len(all_files)} arquivos CSV. Iniciando a análise exploratória...")

for file in all_files:
    file_name = os.path.basename(file)
    try:
        df = pd.read_csv(file, nrows=10000)
        dtypes = df.dtypes.astype(str).to_dict()
        
        with open(file, 'r', encoding='utf-8') as f:
            total_rows = sum(1 for _ in f) - 1 
            
        columns = df.columns.tolist()
        missing_sample = df.isnull().sum().to_dict()
        
        schema_info[file_name] = {
            "total_rows": total_rows,
            "columns": columns,
            "dtypes": dtypes,
            "missing_in_sample": missing_sample,
            "sample_data": df.head(3).to_dict(orient='records')
        }
        print(f"[OK] {file_name}: {total_rows} linhas, {len(columns)} colunas.")
        
    except Exception as e:
        print(f"[ERROR] Erro ao ler {file_name}: {e}")
        schema_info[file_name] = {"error": str(e)}

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(schema_info, f, indent=4, ensure_ascii=False)

print(f"Análise concluída. Resultados salvos em {output_file}")
