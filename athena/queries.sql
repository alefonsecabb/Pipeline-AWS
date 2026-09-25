-- Avaliacao Multidisciplinar - VAREJO_05
-- Consultas Amazon Athena sobre a base tratada varejo05_db.vendas (Glue Data Catalog)
-- Nome da tabela confirmado apos rodar o crawler "processed-vendas-varejo05-crawler".

-- 1. Contagem de registros por ano
SELECT
    year(data) AS ano,
    count(*) AS registros
FROM varejo05_db.vendas
GROUP BY year(data)
ORDER BY ano;

-- 2. Quantidade vendida por loja
SELECT
    loja,
    sum(quantidade_vendida) AS total_vendido
FROM varejo05_db.vendas
GROUP BY loja
ORDER BY total_vendido DESC;

-- 3. Quantidade vendida por categoria e produto
SELECT
    categoria,
    produto,
    sum(quantidade_vendida) AS total_vendido
FROM varejo05_db.vendas
GROUP BY categoria, produto
ORDER BY total_vendido DESC;

-- 4. Evolucao mensal das vendas
SELECT
    date_trunc('month', data) AS mes,
    sum(quantidade_vendida) AS total_vendido
FROM varejo05_db.vendas
GROUP BY date_trunc('month', data)
ORDER BY mes;

-- 5. Verificacao de qualidade dos dados (nulos remanescentes apos tratamento no Glue)
SELECT
    count(*) AS total_linhas,
    sum(CASE WHEN preco IS NULL THEN 1 ELSE 0 END) AS preco_nulo,
    sum(CASE WHEN estoque IS NULL THEN 1 ELSE 0 END) AS estoque_nulo,
    sum(CASE WHEN temperatura_prevista IS NULL THEN 1 ELSE 0 END) AS temperatura_nula,
    sum(CASE WHEN promocao IS NULL THEN 1 ELSE 0 END) AS promocao_nula,
    sum(CASE WHEN categoria IS NULL THEN 1 ELSE 0 END) AS categoria_nula,
    sum(CASE WHEN quantidade_vendida < 0 THEN 1 ELSE 0 END) AS quantidade_negativa
FROM varejo05_db.vendas;

-- 6. (extra) Efeito da promocao na quantidade media vendida -- achado de negocio
SELECT
    promocao,
    round(avg(quantidade_vendida), 2) AS media_vendida,
    count(*) AS n_registros
FROM varejo05_db.vendas
WHERE promocao IS NOT NULL
GROUP BY promocao
ORDER BY promocao;
