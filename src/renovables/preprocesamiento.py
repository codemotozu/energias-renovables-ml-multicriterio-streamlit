"""Transformadores propios del pipeline de las fases 2 y 3 (mismo código, ahora en un módulo importable)."""
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin


class Winsorizador(BaseEstimator, TransformerMixin):
    """Recorta cada columna a los percentiles [inferior, superior] estimados solo en el ajuste."""

    def __init__(self, inferior=0.005, superior=0.995):
        self.inferior, self.superior = inferior, superior

    def fit(self, X, y=None):
        X = pd.DataFrame(X)
        self.feature_names_in_ = np.asarray(X.columns, dtype=object)
        self.n_features_in_ = X.shape[1]
        self.lim_inf_, self.lim_sup_ = X.quantile(self.inferior).values, X.quantile(self.superior).values
        return self

    def transform(self, X):
        return pd.DataFrame(X, columns=self.feature_names_in_).clip(lower=self.lim_inf_, upper=self.lim_sup_, axis=1)

    def get_feature_names_out(self, input_features=None):
        return self.feature_names_in_


class Interacciones(BaseEstimator, TransformerMixin):
    """Productos tecnología × variable (la solar es la referencia); no estima parámetros."""

    def __init__(self, variables=("irradiacion_relativa", "edad_planta", "log_capacidad")):
        self.variables = variables

    def fit(self, X, y=None):
        self.feature_names_in_ = np.asarray(X.columns, dtype=object)
        self.n_features_in_ = X.shape[1]
        self.dummies_ = [c for c in X.columns if c.startswith("tecnologia_")]
        return self

    def transform(self, X):
        X = X.copy()
        for d in self.dummies_:
            for v in self.variables:
                X[f"{d.removeprefix('tecnologia_')} × {v}"] = X[d] * X[v]
        return X

    def get_feature_names_out(self, input_features=None):
        nuevas = [f"{d.removeprefix('tecnologia_')} × {v}" for d in self.dummies_ for v in self.variables]
        return np.concatenate([self.feature_names_in_, nuevas])
