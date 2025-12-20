"""Deterministic forecasting (no LLM).

LEGACY CODE - FROZEN - DO NOT IMPORT
"""
raise RuntimeError(
    "LEGACY CODE IS FROZEN - This file has been moved to legacy_frozen/ and must not be imported. "
    "Use addons/forecast/ as optional microservice instead. See /src/verity/core/ for new implementation."
)

# The code below is preserved for reference only and will never execute
# ============================================================================

"""
This module is used by the orchestrator (AgentService) to produce simple,
audit-friendly forecasts from an already-aggregated time series table.

Design goals:
- Deterministic output (no LLM)
- Fast baseline model (linear trend / ridge)
- Strong validation to avoid garbage forecasts
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ForecastResult:
    """Forecast output for UI + audit."""

    forecast_table: pd.DataFrame
    # Human-readable trace for audit/debug (no code)
    evidence_ref: str


class ForecastAgent:
    """Deterministic baseline forecaster."""

    def _normalize_freq(self, freq: str) -> str:
        """Normalize common frequency codes for modern pandas.

        Pandas 2.3+ deprecates some legacy aliases (e.g. 'M'). We normalize to
        stable start-based aliases so resample/date_range are warning-free.
        """
        f = (freq or "").upper().strip()
        if f == "M":
            return "MS"  # Month start
        if f == "Q":
            return "QS"  # Quarter start
        if f == "Y":
            return "YS"  # Year start
        return f or "MS"

    def _z_from_confidence(self, confidence: float) -> float:
        """Return an approximate z-score for common two-sided confidence levels."""
        c = float(confidence)
        if c <= 0 or c >= 1:
            raise ValueError("confidence debe estar entre 0 y 1")

        # Common two-sided z values
        common = {
            0.80: 1.2816,
            0.90: 1.6449,
            0.95: 1.9600,
            0.99: 2.5758,
        }
        # Snap to nearest common value to avoid needing scipy.
        nearest = min(common.keys(), key=lambda k: abs(k - c))
        return common[nearest]

    def _robust_sigma(self, y: np.ndarray, y_fit: np.ndarray) -> float:
        """Estimate sigma robustly from residuals, with fallback to diffs.

        - Residuals are winsorized to reduce influence from spikes.
        - Primary estimator: MAD * 1.4826
        - Fallback: std(residuals)
        - Last resort: MAD/std of diff(y)
        """
        residuals = (y - y_fit).astype(float)
        residuals = residuals[np.isfinite(residuals)]

        def mad_std(a: np.ndarray) -> float:
            if a.size < 3:
                return 0.0
            med = float(np.median(a))
            mad = float(np.median(np.abs(a - med)))
            return 1.4826 * mad

        sigma = 0.0
        if residuals.size >= 3:
            # Winsorize residuals for sigma estimation only
            if residuals.size >= 10:
                lo_q, hi_q = 0.01, 0.99
            else:
                lo_q, hi_q = 0.05, 0.95

            lo = float(np.quantile(residuals, lo_q))
            hi = float(np.quantile(residuals, hi_q))
            res_clip = np.clip(residuals, lo, hi)

            sigma = mad_std(res_clip)
            if not np.isfinite(sigma) or sigma <= 0:
                sigma = float(np.nanstd(res_clip, ddof=1)) if res_clip.size > 2 else 0.0

        if not np.isfinite(sigma) or sigma <= 0:
            diffs = np.diff(y.astype(float))
            diffs = diffs[np.isfinite(diffs)]
            sigma = mad_std(diffs)
            if not np.isfinite(sigma) or sigma <= 0:
                sigma = float(np.nanstd(diffs, ddof=1)) if diffs.size > 2 else 0.0

        return float(sigma) if np.isfinite(sigma) else 0.0

    def _infer_season_length(self, freq_norm: str) -> int | None:
        """Infer a reasonable seasonal period length for common frequencies."""
        f = (freq_norm or "").upper().strip()
        if f.startswith("W"):
            return 52
        if f in {"MS", "M"}:
            return 12
        if f in {"QS", "Q"}:
            return 4
        if f.startswith("D"):
            return 7
        return None

    def _robust_sigma_from_residuals(self, residuals: np.ndarray) -> float:
        residuals = residuals.astype(float)
        residuals = residuals[np.isfinite(residuals)]
        if residuals.size < 3:
            return 0.0

        # Winsorize
        if residuals.size >= 10:
            lo_q, hi_q = 0.01, 0.99
        else:
            lo_q, hi_q = 0.05, 0.95
        lo = float(np.quantile(residuals, lo_q))
        hi = float(np.quantile(residuals, hi_q))
        res_clip = np.clip(residuals, lo, hi)

        med = float(np.median(res_clip))
        mad = float(np.median(np.abs(res_clip - med)))
        sigma = 1.4826 * mad
        if not np.isfinite(sigma) or sigma <= 0:
            sigma = float(np.nanstd(res_clip, ddof=1)) if res_clip.size > 2 else 0.0
        return float(sigma) if np.isfinite(sigma) else 0.0

    def forecast(
        self,
        table_source: pd.DataFrame,
        *,
        time_col: str,
        y_col: str,
        freq: str,
        horizon: int,
        confidence: float = 0.80,
        model_type: Literal["auto", "linear_trend", "ridge", "seasonal_naive"] = "auto",
        min_points: int = 8,
    ) -> ForecastResult:
        freq_norm = self._normalize_freq(freq)

        z = self._z_from_confidence(confidence)

        if horizon <= 0:
            raise ValueError("horizon debe ser >= 1")

        if time_col not in table_source.columns:
            raise ValueError(f"time_col no existe: {time_col}")
        if y_col not in table_source.columns:
            raise ValueError(f"y_col no existe: {y_col}")

        df = table_source[[time_col, y_col]].copy()

        # Parse + clean
        df[time_col] = pd.to_datetime(df[time_col], errors="coerce", utc=False)
        df[y_col] = pd.to_numeric(df[y_col], errors="coerce")
        df = df.dropna(subset=[time_col, y_col])
        df = df.sort_values(time_col)

        if len(df) < min_points:
            raise ValueError(f"Se requieren al menos {min_points} puntos; encontré {len(df)}")

        # Resample to requested frequency to fill gaps deterministically
        df = df.set_index(time_col)
        # If duplicate timestamps exist (common after grouping), sum them deterministically.
        df = df.groupby(level=0).sum(numeric_only=True)

        # Resample (sum by default for totals); if it's already at freq, this is stable.
        df = df.resample(freq_norm).sum()

        # Fill gaps (controlled): keep as NaN then interpolate linearly, then forward-fill.
        # This avoids dropping periods and keeps horizon aligned.
        df[y_col] = df[y_col].interpolate(method="time")
        df[y_col] = df[y_col].ffill()

        # After fill, drop any leading NaNs
        df = df.dropna(subset=[y_col])

        if len(df) < min_points:
            raise ValueError(
                f"Después de resample/fill se requieren {min_points} puntos; quedaron {len(df)}"
            )

        y = df[y_col].astype(float).to_numpy()
        t = np.arange(len(y), dtype=float)

        chosen_model = model_type
        season_length = None
        if model_type == "auto":
            season_length = self._infer_season_length(freq_norm)
            # Require at least 2 seasons to make the seasonal signal meaningful.
            if season_length and len(y) >= season_length * 2:
                chosen_model = "seasonal_naive"
            else:
                chosen_model = "linear_trend"
        elif model_type == "seasonal_naive":
            season_length = self._infer_season_length(freq_norm)
            if not season_length:
                raise ValueError(f"No se pudo inferir estacionalidad para freq={freq_norm}")
            if len(y) < season_length * 2:
                raise ValueError(
                    f"Se requieren al menos {season_length * 2} puntos para seasonal_naive; encontré {len(y)}"
                )

        # Model
        if chosen_model == "seasonal_naive":
            s = int(season_length or 0)
            if s <= 0:
                raise ValueError("season_length inválido")
            # Fit: y_hat(t) = y(t - s)
            y_fit = np.full_like(y, np.nan, dtype=float)
            y_fit[s:] = y[: len(y) - s]
            # Fill initial region deterministically for table readability
            y_fit = np.where(np.isfinite(y_fit), y_fit, y)

            # Forecast repeats last season
            last_season = y[len(y) - s :]
            reps = int(np.ceil(horizon / s))
            y_hat_future = np.tile(last_season, reps)[:horizon].astype(float)

            # Sigma from seasonal residuals
            residuals = y[s:] - y[: len(y) - s]
            sigma = self._robust_sigma_from_residuals(residuals)
        elif chosen_model == "linear_trend":
            coef = np.polyfit(t, y, deg=1)
            y_fit = np.polyval(coef, t)
            t_future = np.arange(len(y), len(y) + horizon, dtype=float)
            y_hat_future = np.polyval(coef, t_future)
            sigma = self._robust_sigma(y, y_fit)
        else:
            # Ridge for stability (closed-form)
            # y_hat = X (X'X + alpha I)^-1 X' y
            alpha = 1.0
            X = np.vstack([np.ones_like(t), t]).T
            XtX = X.T @ X
            XtX_reg = XtX + alpha * np.eye(XtX.shape[0])
            beta = np.linalg.solve(XtX_reg, X.T @ y)
            y_fit = X @ beta
            t_future = np.arange(len(y), len(y) + horizon, dtype=float)
            Xf = np.vstack([np.ones_like(t_future), t_future]).T
            y_hat_future = Xf @ beta

            sigma = self._robust_sigma(y, y_fit)
        margin = max(0.0, z * sigma)

        # Build timeline
        history_index = df.index
        last_ts = history_index[-1]
        future_index = pd.date_range(start=last_ts, periods=horizon + 1, freq=freq_norm)[1:]

        out = pd.DataFrame(
            {
                "time": list(history_index) + list(future_index),
                "y": list(y) + [np.nan] * horizon,
                "y_hat": list(y_fit) + list(y_hat_future),
                "y_lo": list(y_fit) + list(y_hat_future - margin),
                "y_hi": list(y_fit) + list(y_hat_future + margin),
            }
        )

        # Evidence
        start = history_index[0].isoformat()
        end = history_index[-1].isoformat()
        season_str = f", season_length={season_length}" if season_length else ""
        evidence_ref = (
            f"FORECAST: model={chosen_model}{season_str}, freq={freq_norm} (requested={freq}), horizon={horizon}, "
            f"confidence={confidence:.2f}, points_used={len(history_index)}, range=[{start}..{end}], sigma={sigma:.4f}"
        )

        return ForecastResult(forecast_table=out, evidence_ref=evidence_ref)
