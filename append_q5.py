with open('questoes.md', 'a', encoding='utf-8') as f:
    f.write('\n## Questão 5.2 - Explicação Calendário\n')
    f.write('**1. Por que usar tabela calendário em vez de agrupar direto?**\n')
    f.write('Se agruparmos diretamente a tabela de vendas, os dias em que não houveram vendas não aparecerão no resultado (as linhas somem). O calendário atua como uma "espinha dorsal" (spine), garantindo que todos os dias da semana sejam representados no relatório. O LEFT JOIN acopla as vendas existentes e deixa nulos (convertidos para zero) os dias sem vendas.\n\n')
    f.write('**2. O que aconteceria com a média de vendas?**\n')
    f.write('Se não usássemos o calendário, os dias com "zero vendas" seriam ignorados no cálculo do denominador da média, o que inflaria (aumentaria artificialmente) a média de vendas. Por exemplo, vender R$ 100 na segunda e R$ 0 na terça dá uma média real de R$ 50/dia. Sem o calendário, a terça some e a média calculada pelo banco será de R$ 100/dia. O calendário força a inclusão dos zeros, garantindo a acurácia estatística.\n')
