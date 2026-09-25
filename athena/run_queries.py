"""
Executa as consultas de athena/queries.sql via boto3 e imprime os resultados.
Uso: python run_queries.py
Requer credenciais AWS validas (Learner Lab) e o workgroup "primary" com
OutputLocation configurado (feito em setup).
"""
import time
import boto3

BUCKET = "bigdata-ml-varejo05-768366506781"
DATABASE = "varejo05_db"
OUTPUT_LOCATION = f"s3://{BUCKET}/athena-results/"


def run_query(athena, sql: str):
    resp = athena.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": DATABASE},
        ResultConfiguration={"OutputLocation": OUTPUT_LOCATION},
    )
    qid = resp["QueryExecutionId"]
    while True:
        status = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]
        state = status["State"]
        if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
        time.sleep(1.5)
    if state != "SUCCEEDED":
        reason = status.get("StateChangeReason", "")
        raise RuntimeError(f"Query failed ({state}): {reason}\n{sql}")
    rows = []
    paginator = athena.get_paginator("get_query_results")
    for page in paginator.paginate(QueryExecutionId=qid):
        for row in page["ResultSet"]["Rows"]:
            rows.append([c.get("VarCharValue", "") for c in row["Data"]])
    return rows


def main():
    with open("queries.sql", "r", encoding="utf-8") as f:
        text = f.read()
    statements = [s.strip() for s in text.split(";") if s.strip()]
    athena = boto3.client("athena")
    for i, stmt in enumerate(statements, 1):
        print(f"\n===== Query {i} =====")
        print(stmt[:200].replace("\n", " ") + ("..." if len(stmt) > 200 else ""))
        rows = run_query(athena, stmt)
        for row in rows:
            print(" | ".join(row))


if __name__ == "__main__":
    main()
