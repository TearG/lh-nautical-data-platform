with open('questoes.md', 'a', encoding='utf-8') as f:
    f.write('\n## Pergunta Bônus / Feedback\n')
    f.write('**Em qual questão você teve mais facilidade?**\n')
    f.write('A **Questão 1 (EDA)** e a **Questão 3 (Carregamento dos CSVs)** foram as que trouxeram maior facilidade. Como elas exigiam apenas comandos lineares e diretos (agregações simples em SQL e iteração de ingestão bruta em Python), não houve necessidade de mapear toda a cadeia relacional do banco de dados (Star Schema) nem aplicar transformações matemáticas complexas, como aconteceu nos modelos de previsão (Média Móvel) e no sistema de recomendação (Similaridade de Cosseno).\n')
