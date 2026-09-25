# Relatório Técnico — Avaliação Prática Multidisciplinar
## Infraestrutura de Big Data + Paradigmas e Tecnologias Emergentes

## 1. Identificação

- **Curso:** Ciência de Dados — FATEC
- **Integrantes:** Alexandre da Fonseca, Riquelmy Henrique Silva
- **Dataset atribuído:** VAREJO_05
- **Conta AWS Academy Learner Lab:** 768366506781 (região `us-east-1`)

## 2. Diagrama da arquitetura implementada

Fluxo implementado:

```
[Arquivos locais CSV]
        |
        v
  Amazon S3 (raw/historico/, raw/inferencia/)
        |
        v
  AWS Glue Job "etl-vendas-varejo05"  --(limpeza/consolidacao)-->  S3 (processed/vendas/, Parquet)
        |                                                                  |
        v                                                                  v
  Glue Crawler "processed-vendas-varejo05-crawler"  ---------->  Glue Data Catalog (varejo05_db.vendas)
                                                                            |
                                                                            v
                                                                     Amazon Athena (consultas SQL)
                                                                            |
                                                                            v
                                                    Amazon SageMaker Notebook "varejo05-referencia"
                                                      (feature engineering, treino, avaliacao,
                                                       inferencia sobre dados_inferencia.csv)
                                                                            |
                                                                            v
                                                        S3 (predictions/previsoes.csv)
```

## 3. Organização dos dados no S3

Bucket: `bigdata-ml-varejo05-768366506781`

| Prefixo | Conteúdo |
|---|---|
| `raw/historico/` | `vendas_2024.csv`, `vendas_2025.csv`, `vendas_2026.csv` (dados brutos originais, preservados sem alteração) |
| `raw/inferencia/` | `dados_inferencia.csv` (bruto, esquema diferente do histórico) |
| `raw/LEIA-ME.md` | Dicionário de dados original |
| `processed/vendas/` | Base histórica consolidada e tratada, em Parquet (saída do Glue) |
| `predictions/` | `previsoes.csv` (saída da Etapa 5) |
| `glue-scripts/` | Script PySpark do job de ETL |
| `athena-results/` | Resultados das consultas do Athena |

Históricos e inferência ficam em prefixos separados porque têm esquemas diferentes (inferência
não tem `quantidade_vendida`); os brutos originais nunca são sobrescritos pela etapa de
preparação.

## 4. Problemas encontrados e tratamentos realizados (AWS Glue)

Perfilamento feito sobre os 3 arquivos históricos (44.278 linhas combinadas):

| Problema | Extensão | Tratamento | Justificativa |
|---|---|---|---|
| `categoria` com formatação inconsistente (maiúsculas, espaços) e ~2.408 valores ausentes | ~19% das linhas | Substituída por um dicionário `produto → categoria` construído a partir dos próprios dados (categoria é função determinística de produto — 10 SKUs, 2 por categoria) | Elimina simultaneamente inconsistência de formatação e ausência, sem precisar de heurística de imputação |
| `preco` com sentinela inválido `-99.00` | 132 linhas | Convertido para nulo | Preço negativo não é fisicamente válido; tratado como dado ausente, não como valor real |
| `estoque` com sentinela inválido `9999` | 134 linhas | Convertido para nulo | Muito acima do intervalo normal observado (90–179); indício de erro de coleta/sensor |
| `promocao` com valores mistos `0/1/sim/nao` | ~2.474 nulos + textos | Padronizado para inteiro 0/1 | Necessário para uso como feature numérica/categórica consistente |
| `data` em dois formatos (`yyyy-MM-dd` e `dd/MM/yyyy`) misturados em todos os arquivos | ~1,5% das linhas | Parsing com dois formatos e coalescência | Sem essa etapa, ~1,5% das datas seriam descartadas ou mal interpretadas em qualquer filtro temporal |
| Linhas duplicadas (linha inteira repetida) | 876 linhas (438 pares) | Removidas com `dropDuplicates()` | Duplicatas exatas não agregam informação e inflacionariam contagens/médias |
| `receita_final` com ~2.511 nulos no histórico e 100% ausente na inferência | — | Mantida na tabela tratada (uso descritivo/Athena), mas **excluída das features do modelo** | É apurada só ao final do dia — vazamento de dado (*data leakage*) |

**Resultado:** 44.278 → **43.840 linhas** na base tratada (job Glue `etl-vendas-varejo05`,
log confirmado via CloudWatch). Base gravada em Parquet em `processed/vendas/` e catalogada em
`varejo05_db.vendas` via crawler `processed-vendas-varejo05-crawler`.

Valores ausentes remanescentes (preço, estoque, temperatura) **não foram imputados no Glue** —
a imputação usa apenas estatísticas do conjunto de treino, calculada na Etapa 4, para não
vazar informação de validação/teste para o treino.

## 5. Resultados das consultas Athena e interpretação

Consultas completas em `athena/queries.sql`. Resultados obtidos (base tratada, 43.840 linhas):

**1) Registros por ano:** 2024=14.640, 2025=14.600, 2026=14.600 — volume estável ano a ano,
compatível com o calendário completo (365/366 dias × 4 lojas × 10 produtos, descontadas as
duplicatas removidas).

**2) Quantidade vendida por loja:** LOJA_04 (557.468) > LOJA_03 (502.244) > LOJA_02 (448.233) >
LOJA_01 (393.770) — diferença de ~42% entre a loja de maior e menor volume.

**3) Quantidade vendida por categoria/produto:** produtos de `utilidades` e `alimentos`
lideram o volume (PROD_10 com 215.530 e PROD_02 com 211.864 unidades).

**4) Evolução mensal:** padrão sazonal recorrente nos 3 anos — picos em janeiro e
outubro–dezembro (~57–61 mil un./mês), vale em abril–junho (~41–45 mil un./mês).

**5) Verificação de qualidade (base tratada):** 0 categorias nulas (confirma que a imputação
via dicionário produto→categoria eliminou 100% dos ausentes), 0 quantidades negativas; nulos
remanescentes (a serem tratados só na modelagem, sem vazamento): preço 3.018, estoque 2.488,
temperatura 2.366, promoção 2.442.

**Achados relevantes:**
1. **Efeito da promoção:** quantidade média vendida sobe de **40,27** (sem promoção) para
   **53,68** (com promoção) — alta de ~33%, o que sustenta usar `promocao` como feature preditiva
   forte no modelo.
2. **Sazonalidade mensal:** o vale de abril–junho e o pico de outubro–dezembro/janeiro se repetem
   todos os anos, sugerindo que atributos de calendário (mês) têm valor preditivo e que decisões
   de reposição de estoque devem antecipar esses ciclos.

## 6. Atributos utilizados, divisão temporal e modelo escolhido

**Features do modelo:** `preco`, `estoque`, `temperatura_prevista`, `media_movel_7d`,
`media_movel_28d` (numéricas); `loja`, `produto` (categóricas, one-hot); `promocao`, `mes`,
`dia_semana`, `fim_de_semana` (binárias/discretas). `categoria` foi deliberadamente excluída por
ser redundante com `produto`. `receita_final` foi excluída por vazamento de dado.

**Divisão temporal:**
- Treino: 01/2024–12/2025 (29.240 linhas)
- Validação: 01/2026–06/2026 (7.240 linhas)
- Teste: 07/2026–12/2026 (7.360 linhas)

Estatísticas de imputação (mediana das numéricas, moda de `promocao`) calculadas **apenas no
treino** e reaplicadas em validação/teste/inferência.

**Modelo:** `RandomForestRegressor` (scikit-learn, 300 árvores, profundidade máxima 12),
dentro de um `Pipeline` com `ColumnTransformer` (imputação + one-hot). Referência (baseline):
média histórica de vendas por loja/produto, calculada no treino.

## 7. Comparação das métricas com a previsão de referência

| Conjunto | Baseline MAE | Baseline RMSE | Modelo MAE | Modelo RMSE | Redução MAE |
|---|---|---|---|---|---|
| Validação | 8,58 | 10,34 | 3,66 | 4,70 | ~57% |
| **Teste** | **6,28** | **8,13** | **3,53** | **4,53** | **~44%** |

O RandomForest reduz o erro absoluto médio em ~44% em relação à referência simples no conjunto
de teste (jamais visto durante treino/ajuste), confirmando que preço, estoque, promoção,
calendário e tendência recente carregam sinal preditivo real além da média histórica.

## 8. Inferência e armazenamento

Previsões geradas para os 1.240 registros de `dados_inferencia.csv` (jan/2027), aplicando a
mesma limpeza do Glue e reaproveitando apenas estatísticas do treino. Saída validada: sem
duplicatas de chave, sem valores negativos (`quantidade_prevista` no intervalo observado
~26–77, compatível com o histórico 4–84). Arquivo `previsoes.csv` salvo em
`s3://bigdata-ml-varejo05-768366506781/predictions/previsoes.csv`.

## 9. Evidências de execução

- Notebook `modelagem_varejo05.ipynb` executado de ponta a ponta na instância SageMaker
  `varejo05-referencia` (kernel `conda_python3`), todas as 9 células sem erro.
- Métricas obtidas na execução real no SageMaker conferem exatamente com a validação prévia:
  teste MAE modelo = 3,53 vs. baseline = 6,28.
- `predictions/previsoes.csv` gravado pelo próprio notebook (via boto3, role `LabRole`,
  sem credenciais no código), confirmado no S3 (53.238 bytes, 1.240 linhas).
- Capturas de tela da execução (tabela de métricas e gráfico de importância de atributos)
  anexadas à entrega.
- Instância parada (`stop_notebook_instance`) logo após a execução para não consumir horas
  do Learner Lab desnecessariamente.

## 10. Limitações da solução

- As features de tendência (`media_movel_7d/28d`) usam o último histórico real como valor fixo
  para todo o mês de inferência, em vez de recalcular dia a dia.
- `categoria` foi excluída do modelo por colinearidade com `produto`; o modelo não generalizaria
  para produtos fora do catálogo atual (10 SKUs fixos).
- Imputação por mediana/moda é simples; não captura eventuais padrões nos próprios valores
  ausentes (ex.: falha sistemática de sensor de estoque em determinada loja).
- Modelo não foi publicado como endpoint do SageMaker (não exigido pelo enunciado); inferência
  é em lote, executada diretamente no notebook.
