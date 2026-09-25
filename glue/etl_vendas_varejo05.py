"""
Glue ETL - Avaliacao Multidisciplinar (VAREJO_05)
Consolida vendas_2024/2025/2026.csv (raw/historico/) em uma base unica tratada,
gravada em Parquet (processed/vendas/) e disponibilizada no Glue Data Catalog.

Regras de limpeza aplicadas (justificadas no relatorio tecnico):
  1. data: arquivos misturam formato ISO (yyyy-MM-dd) e BR (dd/MM/yyyy) -> normalizado para date.
  2. preco: contem sentinela invalido -99.00 (132 ocorrencias no historico) -> convertido para nulo.
  3. estoque: contem sentinela invalido 9999 (134 ocorrencias) -> convertido para nulo.
  4. promocao: valores mistos '0'/'1'/'sim'/'nao' -> padronizado para inteiro 0/1.
  5. categoria: e funcao deterministica de produto (cada produto pertence a exatamente uma
     categoria, confirmado no perfilamento dos dados). Formatacao inconsistente (maiusculas,
     espacos) e ausencias (~2.400 linhas) sao corrigidas derivando a categoria a partir de um
     dicionario produto->categoria construido com os proprios dados validos, em vez de apenas
     normalizar texto.
  6. duplicatas: 876 linhas sao duplicatas exatas (linha inteira repetida, 438 pares) -> removidas.
  7. valores ausentes remanescentes (preco, estoque, temperatura_prevista) NAO sao imputados
     aqui: a imputacao usara apenas estatisticas do conjunto de treino, calculada no notebook
     de modelagem (Etapa 4), para evitar vazamento de informacao.
  8. receita_final e mantida na base processada para fins descritivos/Athena, mas NAO deve ser
     usada como feature do modelo: e apurada somente ao encerrar o dia (indisponivel no momento
     da previsao e ausente no arquivo de inferencia) -> vazamento de dado.
"""
import sys
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F
from awsglue.context import GlueContext
from awsglue.job import Job

args = getResolvedOptions(sys.argv, ["JOB_NAME", "BUCKET"])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

bucket = args["BUCKET"]
raw_path = f"s3://{bucket}/raw/historico/"
processed_path = f"s3://{bucket}/processed/vendas/"

df = spark.read.option("header", True).csv(raw_path)
rows_in = df.count()

# 1. Normalizar data (ISO e BR misturados)
df = df.withColumn(
    "data",
    F.coalesce(F.to_date("data", "yyyy-MM-dd"), F.to_date("data", "dd/MM/yyyy")),
)

# 2. Casts numericos
df = (
    df.withColumn("preco", F.col("preco").cast("double"))
    .withColumn("estoque", F.col("estoque").cast("double"))
    .withColumn("temperatura_prevista", F.col("temperatura_prevista").cast("double"))
    .withColumn("receita_final", F.col("receita_final").cast("double"))
    .withColumn("quantidade_vendida", F.col("quantidade_vendida").cast("int"))
)

# 3. Sentinelas invalidas -> nulo
df = df.withColumn("preco", F.when(F.col("preco") == -99.0, None).otherwise(F.col("preco")))
df = df.withColumn("estoque", F.when(F.col("estoque") == 9999.0, None).otherwise(F.col("estoque")))

# 4. promocao -> 0/1
promo_norm = F.lower(F.trim(F.col("promocao")))
df = df.withColumn(
    "promocao",
    F.when(promo_norm.isin("1", "sim"), F.lit(1))
    .when(promo_norm.isin("0", "nao"), F.lit(0))
    .otherwise(F.lit(None))
    .cast("int"),
)

# 5. categoria derivada deterministicamente de produto
cat_norm = F.lower(F.trim(F.col("categoria")))
lookup = (
    df.withColumn("cat_norm", cat_norm)
    .filter(F.col("cat_norm").isNotNull())
    .groupBy("produto")
    .agg(F.first("cat_norm").alias("categoria_lookup"))
)
df = (
    df.drop("categoria")
    .join(lookup, on="produto", how="left")
    .withColumnRenamed("categoria_lookup", "categoria")
)

# 6. Remover duplicatas exatas
df = df.dropDuplicates()
rows_out = df.count()

# Ordem final de colunas
df = df.select(
    "dataset_id",
    "data",
    "loja",
    "produto",
    "categoria",
    "preco",
    "promocao",
    "estoque",
    "quantidade_vendida",
    "temperatura_prevista",
    "receita_final",
)

df.write.mode("overwrite").parquet(processed_path)

print(f"[etl_vendas_varejo05] linhas_entrada={rows_in} linhas_saida={rows_out} duplicatas_removidas={rows_in - rows_out}")

job.commit()
