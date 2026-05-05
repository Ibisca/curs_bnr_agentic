"""Plotly visualization for forecasts.

Reads CSV produced by `src.evaluate` (plot-ready CSV) and generates an interactive Plotly HTML
showing observed values, predicted values, prediction interval, and highlights the final test window
(last 14 days).

Usage:
python -m src.visualization.plotly_viz --plot-csv data/plot_data_*.csv

Outputs:
- HTML interactive file in `reports/` named `forecast_plot_<model>_YYYYMMDD_HHMMSS.html`
- JSON representation in same folder for reproducibility
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

try:
    import plotly.graph_objects as go
except Exception:  # pragma: no cover - optional dependency
    go = None


LOG = logging.getLogger(__name__)


def load_plot_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], dayfirst=False, errors="coerce")
        df = df.set_index("date")
    return df


def build_figure(df: pd.DataFrame, title: Optional[str] = None, highlight_last_n: int = 14) -> "go.Figure":
    if go is None:
        raise ImportError("plotly is required to build the figure. Install plotly.")

    df = df.copy()
    # expected columns: observed, predicted, lower, upper
    x = df.index

    fig = go.Figure()

    # observed
    if "observed" in df.columns:
        fig.add_trace(
            go.Scatter(name="Observed", x=x, y=df["observed"], mode="lines+markers", line=dict(color="black"))
        )

    # predicted
    if "predicted" in df.columns:
        fig.add_trace(
            go.Scatter(name="Predicted", x=x, y=df["predicted"], mode="lines", line=dict(color="blue"))
        )
    elif "pred" in df.columns:
        fig.add_trace(
            go.Scatter(name="Predicted", x=x, y=df["pred"], mode="lines", line=dict(color="blue"))
        )

    # CI band
    lower_col = None
    upper_col = None
    if "lower" in df.columns and "upper" in df.columns:
        lower_col = "lower"
        upper_col = "upper"
    elif "yhat_lower" in df.columns and "yhat_upper" in df.columns:
        lower_col = "yhat_lower"
        upper_col = "yhat_upper"

    if lower_col and upper_col:
        fig.add_trace(
            go.Scatter(
                name="CI Upper",
                x=x,
                y=df[upper_col],
                mode="lines",
                line=dict(width=0),
                showlegend=False,
            )
        )
        fig.add_trace(
            go.Scatter(
                name="Confidence Interval",
                x=x,
                y=df[lower_col],
                mode="lines",
                line=dict(width=0),
                fill="tonexty",
                fillcolor="rgba(0,100,80,0.2)",
                showlegend=True,
            )
        )

    # highlight last N observations (fallback to rectangle if add_vrect isn't available)
    if highlight_last_n > 0:
        valid_idx = df.index
        if len(valid_idx) >= highlight_last_n:
            start = valid_idx[-highlight_last_n]
            end = valid_idx[-1]
            # Prefer add_vrect (available in newer plotly). If missing, use add_shape rect in paper coordinates.
            try:
                fig.add_vrect(
                    x0=start,
                    x1=end,
                    fillcolor="LightSalmon",
                    opacity=0.2,
                    layer="below",
                    line_width=0,
                    annotation_text="Test window",
                    annotation_position="top left",
                )
            except Exception:
                # fallback for older plotly versions: add a filled rectangle via layout shapes and add an annotation
                fig.add_shape(
                    type="rect",
                    x0=start,
                    x1=end,
                    y0=0,
                    y1=1,
                    xref="x",
                    yref="paper",
                    fillcolor="LightSalmon",
                    opacity=0.2,
                    layer="below",
                    line_width=0,
                )
                try:
                    fig.add_annotation(x=start, y=1.02, xref="x", yref="paper", text="Test window", showarrow=False, align="left")
                except Exception:
                    # last-resort: ignore annotation if unavailable
                    pass

    fig.update_layout(
        title=title or "Forecast vs Observed",
        xaxis_title="Date",
        yaxis_title="Rate",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig


def save_figure(fig: "go.Figure", out_dir: Path, model_name: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    html_path = out_dir / f"forecast_plot_{model_name}_{timestamp}.html"
    json_path = out_dir / f"forecast_plot_{model_name}_{timestamp}.json"

    # save HTML
    try:
        fig.write_html(str(html_path), include_plotlyjs="cdn")
        LOG.info("Saved interactive plot to %s", html_path)
    except Exception as e:
        LOG.exception("Failed to save HTML plot: %s", e)

    # save JSON representation
    try:
        fig_json = fig.to_json()
        json_path.write_text(fig_json)
        LOG.info("Saved figure JSON to %s", json_path)
    except Exception as e:
        LOG.exception("Failed to save figure JSON: %s", e)

    return html_path


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--plot-csv", required=True, help="CSV file generated by evaluate.py (plot-ready)")
    parser.add_argument("--model", required=False, help="Model name to include in output filename (optional)")
    parser.add_argument("--out-dir", default="reports", help="Output directory for saved plots")
    parser.add_argument("--highlight-days", type=int, default=14, help="Number of last days to highlight (default 14)")
    args = parser.parse_args()

    plot_csv = Path(args.plot_csv)
    df = load_plot_data(plot_csv)
    model_name = args.model or plot_csv.stem
    title = f"Forecast Plot - {model_name}"

    fig = build_figure(df, title=title, highlight_last_n=args.highlight_days)
    out = save_figure(fig, Path(args.out_dir), model_name)
    print(f"Saved plot: {out}")


if __name__ == "__main__":
    main()
