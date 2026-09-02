import os
import csv
import re

def infer_type(value):
    """Infere o tipo de dado de uma string (Foco em PostgreSQL)."""
    value = value.strip()
    if not value:
        return None
    
    # Verifica se é um número inteiro (ex: 12, -5)
    if re.match(r'^-?\d+$', value):
        return 'INTEGER'
        
    # Verifica se é um número decimal (ex: 12.5, -4.99)
    if re.match(r'^-?\d+\.\d+$', value):
        return 'NUMERIC'
        
    # Verifica se é data ou timestamp (ex: 2024-12-31 ou 2024-12-31 15:30:00)
    if re.match(r'^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?(\.\d+)?$', value):
        return 'TIMESTAMP'
        
    # Qualquer outro caso, assumimos que é texto genérico
    return 'VARCHAR'

def resolve_type(types_set):
    """Resolve conflitos de tipos encontrados em uma mesma coluna."""
    if not types_set:
        return 'VARCHAR' # Se todas as linhas analisadas foram vazias
    if 'VARCHAR' in types_set:
        return 'VARCHAR'
    if 'NUMERIC' in types_set and 'TIMESTAMP' in types_set:
        return 'VARCHAR'
    if 'NUMERIC' in types_set:
        return 'NUMERIC'
    if 'TIMESTAMP' in types_set:
        return 'TIMESTAMP'
    if 'INTEGER' in types_set:
        return 'INTEGER'
    return 'VARCHAR'

def process_csv(csv_path):
    """Lê um CSV e retorna o nome da tabela e seus tipos de colunas detectados."""
    table_name = os.path.basename(csv_path).replace('.csv', '')
    
    # Fallback encoding latin1 para evitar quebra com caracteres do Windows
    with open(csv_path, 'r', encoding='latin1') as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
        except StopIteration:
            return table_name, {}
            
        tracker = {header: set() for header in headers}
        
        # Lemos as primeiras 100 linhas de amostragem para inferir o tipo
        for row_idx, row in enumerate(reader):
            if row_idx >= 100:
                break
            for i, value in enumerate(row):
                if i < len(headers):
                    detected_type = infer_type(value)
                    if detected_type:
                        tracker[headers[i]].add(detected_type)
                        
    # Consolida o tipo final de cada coluna
    col_types = {header: resolve_type(tracker[header]) for header in headers}
    return table_name, col_types

def main():
    input_dir = '1-lh_nautical_csv'
    output_file = 'schema.sql'
    sql_statements = []
    
    if not os.path.exists(input_dir):
        print(f"Erro: O diretório '{input_dir}' não foi encontrado.")
        return
        
    print("Analisando arquivos CSV e inferindo tipos...")
    for filename in sorted(os.listdir(input_dir)):
        if filename.endswith('.csv'):
            csv_path = os.path.join(input_dir, filename)
            table_name, col_types = process_csv(csv_path)
            
            if not col_types:
                continue
                
            # Monta o bloco CREATE TABLE para PostgreSQL
            lines = [f"CREATE TABLE {table_name} ("]
            col_defs = []
            
            for col, ctype in col_types.items():
                # Envolvemos o nome da coluna em aspas duplas (padrão Postgres) 
                # para evitar conflitos com palavras reservadas como "user" ou "order"
                col_defs.append(f"    \"{col}\" {ctype}")
            
            lines.append(",\n".join(col_defs))
            lines.append(");\n")
            
            sql_statements.append("\n".join(lines))
            print(f" - Tabela '{table_name}' mapeada com {len(col_types)} colunas.")
                
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(sql_statements))
        
    print(f"\nSucesso! Esquema DDL gerado em: {output_file}")

if __name__ == '__main__':
    main()
