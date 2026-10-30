"""Índices espectrais por diferença normalizada (R2.8, R2.9).

Recebem reflectância (já convertida pelo `reader`) e a máscara `valid`.
"""

import numpy as np

# Abaixo disso o denominador é tratado como zero.
MIN_DENOMINATOR = 1e-6


def normalized_difference(a: np.ndarray, b: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """`(a − b) / (a + b)` em float32, com `NaN` fora de `valid`.

    Pixel válido com `a + b` zero ou negativo (reflectância ≤ 0 em pixel muito
    escuro, por causa do offset de −0,1) vale 0: sem sinal, em vez de `inf`,
    `nan` ou uma razão de sinal invertido. O resultado fica em [−1, 1].
    """
    a = a.astype(np.float32, copy=False)
    b = b.astype(np.float32, copy=False)
    denominator = a + b
    computable = valid & (denominator > MIN_DENOMINATOR)

    result = np.full(a.shape, np.nan, dtype=np.float32)
    result[valid] = 0.0
    result[computable] = (a[computable] - b[computable]) / denominator[computable]
    return np.clip(result, -1.0, 1.0, out=result)


def ndvi(red: np.ndarray, nir: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """NDVI = (NIR − vermelho) / (NIR + vermelho) (Rouse et al., 1974)."""
    return normalized_difference(nir, red, valid)


def ndwi(green: np.ndarray, nir: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """NDWI = (verde − NIR) / (verde + NIR) (McFeeters, 1996); água fica positiva."""
    return normalized_difference(green, nir, valid)


def gndvi(green: np.ndarray, nir: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """GNDVI = (NIR − verde) / (NIR + verde) (Gitelson, Kaufman e Merzlyak, 1996)."""
    return normalized_difference(nir, green, valid)
