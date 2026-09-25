import glob
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

# ---------------------------------------------------------------
# 1) Carregar base tratada (Glue) e preparar features
# ---------------------------------------------------------------
df = pd.concat([pd.read_parquet(f) for f in glob.glob("*.parquet")], ignore_index=True)
df["data"] = pd.to_datetime(df["data"])
df = df.sort_values(["loja", "produto", "data"]).reset_index(drop=True)

df["mes"] = df["data"].dt.month
df["dia_semana"] = df["data"].dt.dayofweek
df["fim_de_semana"] = df["dia_semana"].isin([5, 6]).astype(int)

grp = df.groupby(["loja", "produto"])["quantidade_vendida"]
df["media_movel_7d"] = grp.transform(lambda s: s.shift(1).rolling(7, min_periods=1).mean())
df["media_movel_28d"] = grp.transform(lambda s: s.shift(1).rolling(28, min_periods=1).mean())

FEATURES_NUM = ["preco", "estoque", "temperatura_prevista", "media_movel_7d", "media_movel_28d"]
FEATURES_CAT = ["loja", "produto"]
FEATURES_BIN = ["promocao", "mes", "dia_semana", "fim_de_semana"]
X_cols = FEATURES_NUM + FEATURES_CAT + FEATURES_BIN
TARGET = "quantidade_vendida"

train = df[(df["data"] >= "2024-01-01") & (df["data"] <= "2025-12-31")].copy()
val = df[(df["data"] >= "2026-01-01") & (df["data"] <= "2026-06-30")].copy()
test = df[(df["data"] >= "2026-07-01") & (df["data"] <= "2026-12-31")].copy()

promo_mode = train["promocao"].mode()[0]
for part in (train, val, test):
    part["promocao"] = part["promocao"].fillna(promo_mode)

preprocess = ColumnTransformer([
    ("num", SimpleImputer(strategy="median"), FEATURES_NUM),
    ("cat", OneHotEncoder(handle_unknown="ignore"), FEATURES_CAT),
], remainder="passthrough")

model = Pipeline([
    ("prep", preprocess),
    ("rf", RandomForestRegressor(n_estimators=300, max_depth=12, random_state=42, n_jobs=-1)),
])
model.fit(train[X_cols], train[TARGET])

baseline_map = train.groupby(["loja", "produto"])[TARGET].mean()
global_mean = train[TARGET].mean()

def baseline_predict(part):
    keys = list(zip(part["loja"], part["produto"]))
    return np.array([baseline_map.get(k, global_mean) for k in keys])

for name, part in [("val", val), ("test", test)]:
    pred_m = model.predict(part[X_cols])
    pred_b = baseline_predict(part)
    y = part[TARGET]
    print(f"{name}: baseline MAE={mean_absolute_error(y,pred_b):.3f} RMSE={mean_squared_error(y,pred_b)**0.5:.3f} | "
          f"modelo MAE={mean_absolute_error(y,pred_m):.3f} RMSE={mean_squared_error(y,pred_m)**0.5:.3f}")

# ---------------------------------------------------------------
# 2) Preparar dados_inferencia.csv com a MESMA limpeza do Glue
# ---------------------------------------------------------------
inf_raw = pd.read_csv("../dados_inferencia.csv", dtype=str)

inf = inf_raw.copy()
inf["data"] = pd.to_datetime(inf["data"], format="ISO8601", errors="coerce")
mask_bad = inf["data"].isna()
inf.loc[mask_bad, "data"] = pd.to_datetime(inf_raw.loc[mask_bad, "data"], format="%d/%m/%Y", errors="coerce")

inf["preco"] = pd.to_numeric(inf["preco"], errors="coerce")
inf.loc[inf["preco"] == -99, "preco"] = np.nan
inf["estoque"] = pd.to_numeric(inf["estoque"], errors="coerce")
inf.loc[inf["estoque"] == 9999, "estoque"] = np.nan
inf["temperatura_prevista"] = pd.to_numeric(inf["temperatura_prevista"], errors="coerce")

promo_norm = inf["promocao"].str.strip().str.lower()
inf["promocao"] = promo_norm.map({"1": 1, "sim": 1, "0": 0, "nao": 0}).astype("float")
inf["promocao"] = inf["promocao"].fillna(promo_mode)

# categoria: mesmo dicionario produto->categoria aprendido na base historica (nao usado como feature, so por consistencia)
cat_lookup = (
    df.assign(cat_norm=df["categoria"])
    .dropna(subset=["cat_norm"])
    .drop_duplicates("produto")
    .set_index("produto")["cat_norm"]
)
inf["categoria"] = inf["produto"].map(cat_lookup)

inf["mes"] = inf["data"].dt.month
inf["dia_semana"] = inf["data"].dt.dayofweek
inf["fim_de_semana"] = inf["dia_semana"].isin([5, 6]).astype(int)

# media movel: ultimos 7/28 dias de historico real (ate 2026-12-31) por loja/produto
ultimo_hist = df.sort_values("data").groupby(["loja", "produto"]).tail(28)
mm7 = ultimo_hist.groupby(["loja", "produto"]).apply(lambda g: g.tail(7)["quantidade_vendida"].mean(), include_groups=False)
mm28 = ultimo_hist.groupby(["loja", "produto"])["quantidade_vendida"].mean()
inf["media_movel_7d"] = inf.set_index(["loja", "produto"]).index.map(mm7)
inf["media_movel_28d"] = inf.set_index(["loja", "produto"]).index.map(mm28)

pred = model.predict(inf[X_cols])
pred = np.clip(pred, 0, None)

saida = inf[["dataset_id", "data", "loja", "produto"]].copy()
saida["data"] = saida["data"].dt.strftime("%Y-%m-%d")
saida["quantidade_prevista"] = np.round(pred, 2)

print("\nprevisoes shape:", saida.shape)
print("chaves duplicadas:", saida.duplicated(subset=["dataset_id", "data", "loja", "produto"]).sum())
print("negativos:", (saida["quantidade_prevista"] < 0).sum())
print(saida.describe())
print(saida.head(10))

saida.to_csv("previsoes_dev.csv", index=False)
