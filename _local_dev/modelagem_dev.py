import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error

import glob
df = pd.concat([pd.read_parquet(f) for f in glob.glob("*.parquet")], ignore_index=True)
df["data"] = pd.to_datetime(df["data"])
df = df.sort_values(["loja", "produto", "data"]).reset_index(drop=True)

# ---- Atributos de calendario (disponiveis antes da venda) ----
df["mes"] = df["data"].dt.month
df["dia_semana"] = df["data"].dt.dayofweek
df["fim_de_semana"] = df["dia_semana"].isin([5, 6]).astype(int)

# ---- Atributos de tendencia (media movel usando so o passado, por loja/produto) ----
grp = df.groupby(["loja", "produto"])["quantidade_vendida"]
df["media_movel_7d"] = grp.transform(lambda s: s.shift(1).rolling(7, min_periods=1).mean())
df["media_movel_28d"] = grp.transform(lambda s: s.shift(1).rolling(28, min_periods=1).mean())

FEATURES_NUM = ["preco", "estoque", "temperatura_prevista", "media_movel_7d", "media_movel_28d"]
FEATURES_CAT = ["loja", "produto"]
FEATURES_BIN = ["promocao", "mes", "dia_semana", "fim_de_semana"]
TARGET = "quantidade_vendida"

train_mask = (df["data"] >= "2024-01-01") & (df["data"] <= "2025-12-31")
val_mask = (df["data"] >= "2026-01-01") & (df["data"] <= "2026-06-30")
test_mask = (df["data"] >= "2026-07-01") & (df["data"] <= "2026-12-31")

train, val, test = df[train_mask], df[val_mask], df[test_mask]
print("train/val/test sizes:", len(train), len(val), len(test))

# imputar promocao com a moda do treino
promo_mode = train["promocao"].mode()[0]
for part in (train, val, test):
    part["promocao"] = part["promocao"].fillna(promo_mode)

X_cols = FEATURES_NUM + FEATURES_CAT + FEATURES_BIN

preprocess = ColumnTransformer([
    ("num", SimpleImputer(strategy="median"), FEATURES_NUM),
    ("cat", OneHotEncoder(handle_unknown="ignore"), FEATURES_CAT),
], remainder="passthrough")

model = Pipeline([
    ("prep", preprocess),
    ("rf", RandomForestRegressor(n_estimators=300, max_depth=12, random_state=42, n_jobs=-1)),
])

X_train, y_train = train[X_cols], train[TARGET]
X_val, y_val = val[X_cols], val[TARGET]
X_test, y_test = test[X_cols], test[TARGET]

model.fit(X_train, y_train)

# ---- baseline: media historica (treino) por loja/produto ----
baseline_map = train.groupby(["loja", "produto"])[TARGET].mean()
global_mean = train[TARGET].mean()

def baseline_predict(part):
    keys = list(zip(part["loja"], part["produto"]))
    return np.array([baseline_map.get(k, global_mean) for k in keys])

for name, X, y, part in [("val", X_val, y_val, val), ("test", X_test, y_test, test)]:
    pred_model = model.predict(X)
    pred_base = baseline_predict(part)
    mae_m = mean_absolute_error(y, pred_model)
    rmse_m = mean_squared_error(y, pred_model) ** 0.5
    mae_b = mean_absolute_error(y, pred_base)
    rmse_b = mean_squared_error(y, pred_base) ** 0.5
    print(f"\n=== {name} ===")
    print(f"baseline  MAE={mae_b:.3f} RMSE={rmse_b:.3f}")
    print(f"modelo    MAE={mae_m:.3f} RMSE={rmse_m:.3f}")
