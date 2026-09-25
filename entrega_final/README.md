# Entrega — Avaliação Multidisciplinar (VAREJO_05)

Alexandre da Fonseca, Riquelmy Henrique Silva

## Conteúdo desta pasta

- `relatorio_tecnico.md` — relatório técnico completo (identificação, arquitetura, problemas de
  dados, consultas Athena, modelagem, métricas, limitações). **Ainda em Markdown** — falta
  exportar para PDF (copiar para Word/Google Docs, colar a imagem do diagrama do link indicado
  no relatório, exportar como PDF) e revisar antes de entregar.
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

## O que ainda falta (revisão manual)

1. Conferir o relatório técnico (nomes, números, texto).
2. Exportar `relatorio_tecnico.md` para PDF, colando o diagrama de arquitetura publicado em
   https://claude.ai/code/artifact/60c33868-63ff-4383-a444-90d59759ccfb (print ou export da página).
3. Opcional: tirar mais prints do console AWS (S3, Glue, Athena) para reforçar as evidências —
   as que já estão aqui vieram do notebook e da CLI, mas o enunciado aceita qualquer evidência
   que comprove a execução.
4. Confirmar com o Riquelmy que ele conhece e consegue explicar a solução (exigido no enunciado).

## Recursos AWS ativos (conta Learner Lab 768366506781, região us-east-1)

- Bucket S3: `bigdata-ml-varejo05-768366506781`
- Glue Database: `varejo05_db` (tabela `vendas`)
- Glue Job: `etl-vendas-varejo05`
- Glue Crawler: `processed-vendas-varejo05-crawler`
- SageMaker Notebook Instance: `varejo05-referencia` (**parada** após a execução — inicie de
  novo com `start_notebook_instance` se precisar reabrir o Jupyter)

Lembrete do enunciado: interrompa recursos de computação quando não estiverem em uso — a
instância do SageMaker já foi parada; não há outro recurso de cômputo ativo além dela.
