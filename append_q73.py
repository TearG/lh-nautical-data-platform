with open('questoes.md', 'a', encoding='utf-8') as f:
    f.write('\n## Questão 7.3 - Explicação Metodológica\n')
    f.write('**1. Como a matriz foi construída?**\n')
    f.write('Realizamos um join entre as tabelas de pedidos e produtos para mapear o par (id_cliente, id_produto). Agrupamos os dados para marcar com "1" caso o cliente tenha comprado o produto ao menos uma vez na vida. Em seguida, usamos a função de Pivot para transformar a base em uma matriz larga (linhas = clientes, colunas = produtos), preenchendo com "0" as interseções de produtos que não foram comprados.\n\n')
    f.write('**2. O que significa a similaridade de cosseno nesse contexto?**\n')
    f.write('A similaridade de cosseno mede o "ângulo" entre dois vetores de produtos no espaço multidimensional de clientes. Em termos de negócio, ela calcula o quão sobreposta é a base de compradores de dois itens. Se o Motor A e o Cabo B possuem uma similaridade próxima de 1, significa que eles compartilham quase exatamente os mesmos clientes (quem compra um, quase sempre compra o outro).\n\n')
    f.write('**3. Uma limitação desse método de recomendação.**\n')
    f.write('O problema do **"Cold Start" (Início Frio)** e o **Sparsity (Matriz Esparsa)**. Esse modelo é totalmente cego para as características físicas do produto. Se a LH Nautical lançar um motor novo e incrivelmente bom hoje, o algoritmo jamais o recomendará, pois como o produto não possui histórico de vendas, seu vetor será inteiramente zerado, e a similaridade de cosseno com os outros itens será 0.\n')
