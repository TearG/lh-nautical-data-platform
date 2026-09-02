import os
import csv
import re

def infer_type(value):
    """Infere o tipo de dado de uma string."""
    value = value.strip()
    if not value:
        return None
    # Verifica se é um número inteiro
    if re.match(r'^-?\d+$', value):
        return 'INTEGER'
    # Verifica se é um número decimal
    if re.match(r'^-?\d+\.\d+$', value):
        return 'NUMERIC'
    # Verifica se é data ou timestamp (formato YYYY-MM-DD ou YYYY-MM-DD HH:MM:SS)
    if re.match(r'^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?(\.\d+)?$', value):
        return 'TIMESTAMP'
    # Qualquer outro caso, assumimos que é texto
    return 'VARCHAR'

def resolve_type(types_set):
    """Resolve conflitos de tipos encontrados em uma mesma coluna."""
    if not types_set:
        return 'VARCHAR' # Se todas as linhas foram vazias
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
    
    with open(csv_path, 'r', encoding='latin1') as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
        except StopIteration:
            return table_name, {}
            
        tracker = {header: set() for header in headers}
        
        # Lemos até as primeiras 100 linhas para inferir o tipo
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
        
    print("Analisando arquivos CSV...")
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
                # Envolvemos o nome da coluna em aspas para evitar conflito com palavras reservadas
                col_defs.append(f"    \"{col}\" {ctype}")
            
            lines.append(",\n".join(col_defs))
            lines.append(");\n")
            
            sql_statements.append("\n".join(lines))
            print(f" - Tabela '{table_name}' mapeada com {len(col_types)} colunas.")
                
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(sql_statements))
        
    print(f"\nSucesso! Arquivo gerado em: {output_file}")

if __name__ == '__main__':
    main()
