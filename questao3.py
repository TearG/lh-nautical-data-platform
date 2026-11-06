import os
import pandas as pd
from sqlalchemy import create_engine

DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'lh_nautical')

DATABASE_URI = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
engine = create_engine(DATABASE_URI)

def load_data():
    input_dir = '1-lh_nautical_csv'
    
    if not os.path.exists(input_dir):
        print(f"Erro: O diretório '{input_dir}' não foi encontrado.")
        return

    print("Iniciando processo de ingestão bruta dos dados...")
    
    for filename in sorted(os.listdir(input_dir)):
        if filename.endswith('.csv'):
            table_name = filename.replace('.csv', '')
            csv_path = os.path.join(input_dir, filename)
            
            try:
                df = pd.read_csv(csv_path, encoding='latin1')
                df.to_sql(name=table_name, con=engine, if_exists='append', index=False, chunksize=10000)
                print(f"[OK] - Tabela '{table_name}': {len(df)} linhas inseridas com sucesso.")
            except Exception as e:
                print(f"[ERRO] - Falha ao carregar a tabela '{table_name}': {e}")

if __name__ == "__main__":
    load_data()
