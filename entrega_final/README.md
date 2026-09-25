# Entrega — Avaliação Multidisciplinar (VAREJO_05)

Alexandre da Fonseca, Riquelmy Henrique Silva

## Conteúdo desta pasta

- `relatorio_tecnico.md` — relatório técnico completo (identificação, arquitetura, problemas de
  dados, consultas Athena, modelagem, métricas, limitações). Versão Word em
  `relatorio_tecnico.docx`.
- `previsoes.csv` — saída oficial da Etapa 5, baixada de
  `s3://bigdata-ml-varejo05-768366506781/predictions/previsoes.csv` (1.240 linhas).
- `codigo/`
  - `etl_vendas_varejo05.py` — script PySpark do job Glue (Etapa 2).
  - `queries.sql` — as 6 consultas Athena (Etapa 3).
  - `run_queries.py` — script para reexecutar as consultas via boto3.
  - `modelagem_varejo05.ipynb` — notebook de modelagem e inferência (Etapas 4 e 5), executado
    com sucesso na instância SageMaker `varejo05-referencia`.
- `evidencias/`
  - `sagemaker_avaliacao_mae_rmse.jpg` — print da tabela de métricas (MAE/RMSE) rodando no
    notebook do SageMaker.
  - `sagemaker_feature_importance.jpg` — print do gráfico de importância de atributos.
  - `execucao_aws.txt` — estrutura final do bucket S3, status do job/crawler do Glue e schema
    da tabela no Data Catalog (coletado via AWS SDK/CLI, direto da conta AWS).
  - `resultados_athena.txt` — saída completa das 6 consultas do Athena.

## Recursos AWS utilizados (conta Learner Lab 768366506781, região us-east-1)

- Bucket S3: `bigdata-ml-varejo05-768366506781`
- Glue Database: `varejo05_db` (tabela `vendas`)
- Glue Job: `etl-vendas-varejo05`
- Glue Crawler: `processed-vendas-varejo05-crawler`
- SageMaker Notebook Instance: `varejo05-referencia` (**parada** após a execução — inicie de
  novo com `start_notebook_instance` se precisar reabrir o Jupyter)
