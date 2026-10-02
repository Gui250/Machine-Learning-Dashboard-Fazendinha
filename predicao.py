"""Previsão mensal com scikit-learn: tendência linear + sazonalidade pelo modelo escolhido."""
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge

MODELOS = {
    "Regressão linear": lambda: Ridge(alpha=1.0),
    "Random Forest": lambda: RandomForestRegressor(n_estimators=300, min_samples_leaf=2, random_state=42),
    "Gradient Boosting": lambda: GradientBoostingRegressor(n_estimators=200, max_depth=2, learning_rate=0.05, random_state=42),
}


def _sazonal(datas):
    meses = pd.DatetimeIndex(datas).month.to_numpy()
    return np.eye(12)[meses - 1]


def _ajustar(datas, y, nome_modelo):
    t = np.arange(len(y)).reshape(-1, 1)
    tendencia = LinearRegression().fit(t, y)
    sazonal = MODELOS[nome_modelo]().fit(_sazonal(datas), y - tendencia.predict(t))
    return lambda idx, d: tendencia.predict(idx.reshape(-1, 1)) + sazonal.predict(_sazonal(d))


def prever(serie: pd.Series, horizonte: int, nome_modelo: str, holdout: int = 6):
    """serie: valores mensais indexados por data (início do mês).

    Retorna (previsao, metricas). previsao tem colunas data, previsto, minimo, maximo.
    O intervalo usa o erro do período de validação (últimos `holdout` meses).
    """
    serie = serie.dropna().sort_index()
    y = serie.to_numpy(dtype=float)
    datas = serie.index
    n = len(y)
    if n < holdout + 12:
        raise ValueError(f"São necessários ao menos {holdout + 12} meses de histórico; o filtro atual tem {n}.")

    # validação: treina sem os últimos meses e mede o erro neles
    f_val = _ajustar(datas[:-holdout], y[:-holdout], nome_modelo)
    pred_val = f_val(np.arange(n - holdout, n), datas[-holdout:])
    erro = y[-holdout:] - pred_val
    mae = float(np.mean(np.abs(erro)))
    mape = float(np.mean(np.abs(erro) / np.where(y[-holdout:] == 0, np.nan, np.abs(y[-holdout:]))) * 100)

    # modelo final com todo o histórico
    f = _ajustar(datas, y, nome_modelo)
    futuras = pd.date_range(datas[-1] + pd.offsets.MonthBegin(1), periods=horizonte, freq="MS")
    previsto = f(np.arange(n, n + horizonte), futuras)
    margem = 1.96 * float(np.std(erro, ddof=1))
    previsao = pd.DataFrame({"data": futuras, "previsto": previsto, "minimo": previsto - margem, "maximo": previsto + margem})
    validacao = pd.DataFrame({"data": datas[-holdout:], "real": y[-holdout:], "previsto": pred_val})
    return previsao, {"MAE": mae, "MAPE": mape, "validacao": validacao}


if __name__ == "__main__":
    idx = pd.date_range("2023-01-01", periods=36, freq="MS")
    s = pd.Series(1000 + 10 * np.arange(36) + 100 * np.sin(idx.month / 12 * 2 * np.pi), index=idx)
    for nome in MODELOS:
        prev, m = prever(s, 6, nome)
        assert len(prev) == 6 and prev["data"].iloc[0] == pd.Timestamp("2026-01-01")
        assert m["MAPE"] < 5, (nome, m["MAPE"])
    print("ok")
