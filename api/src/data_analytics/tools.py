from src.agent.context import current
from src.agent.server import tool
from src.data_analytics.algorithms import (
    association,
    basket,
    causal,
    clustering,
    cohort,
    compare,
    descriptive,
    dimreduction,
    dtypes,
    feature_computation,
    insights,
    interpretation,
    supervised,
    timeseries,
)
from src.data_analytics.schemas import (
    AnalysisResultResponse,
    CategoricalColumnsResponse,
    ClassifyNominalResponse,
    ColumnTypeClearedResponse,
    ColumnTypeResponse,
    TrainedModelResponse,
    UnclassifiedColumn,
)
from src.data_analytics.shared.results import Result
from src.data_analytics.store import models as model_store
from src.data_analytics.store.pgtable import resolve_table


def _store(table: str):
    return resolve_table(current(), table)


def _result(res: Result) -> AnalysisResultResponse:
    return AnalysisResultResponse.from_result(res)


@tool(desk="analytics")
def profile(table: str) -> AnalysisResultResponse:
    """Per-column type, missingness, cardinality and distribution summary for a table."""
    return _result(descriptive.profile(_store(table)))


@tool(desk="analytics")
def detect_outliers(table: str, column: str) -> AnalysisResultResponse:
    """Flag outliers in a numeric column (IQR + z-score) and write the flags back as
    columns. Workspace tables only."""
    return _result(descriptive.detect_outliers(_store(table), column))


@tool(desk="analytics")
def analyze_association(table: str, col_a: str, col_b: str) -> AnalysisResultResponse:
    """Test the association between two columns; the statistical test is chosen
    deterministically from the column types."""
    return _result(association.analyze_association(_store(table), col_a, col_b))


@tool(desk="analytics")
def association_matrix(table: str) -> AnalysisResultResponse:
    """Pairwise association strength across all comparable column pairs of a table."""
    return _result(descriptive.association_matrix(_store(table)))


@tool(desk="analytics")
def list_categorical_columns(table: str) -> CategoricalColumnsResponse:
    """Worklist of columns still at the coarse `categorical` label, with distinct
    counts and sample values. Modeling refuses to run until each is refined to
    nominal or ordinal."""
    store = _store(table)
    frame = store.get_frame()
    out = []
    for col in store.columns():
        if dtypes.classify_column(col, store) == "categorical":
            series = frame[col].dropna()
            out.append(
                UnclassifiedColumn(
                    column=col,
                    distinct=int(series.nunique()),
                    sample=[str(v) for v in series.unique()[:10]],
                )
            )
    return CategoricalColumnsResponse(table=store.key, unclassified=out, n=len(out))


@tool(desk="analytics")
def set_column_type(table: str, column: str, type: str) -> ColumnTypeResponse:
    """Assign `categorical_nominal` (unordered) or `categorical_ordinal` (ordered)
    to a column. Other types are auto-detected and not settable."""
    if type not in dtypes.SETTABLE_TYPES:
        raise ValueError(
            f"set_column_type accepts only {sorted(dtypes.SETTABLE_TYPES)}; got {type!r}."
        )
    store = _store(table)
    store.set_cached_type(column, type)
    return ColumnTypeResponse(table=store.key, column=column, type=type)


@tool(desk="analytics")
def unset_column_type(table: str, column: str) -> ColumnTypeClearedResponse:
    """Clear a column's assigned type so it is re-detected on next use."""
    store = _store(table)
    store.unset_cached_type(column)
    return ColumnTypeClearedResponse(table=store.key, column=column)


@tool(desk="analytics")
def classify_as_nominal(table: str) -> ClassifyNominalResponse:
    """Refine every still-unclassified categorical column on the table to nominal in
    one call; then selectively mark the genuinely ordered ones ordinal."""
    store = _store(table)
    refined = []
    for col in store.columns():
        if dtypes.classify_column(col, store) == "categorical":
            store.set_cached_type(col, "categorical_nominal")
            refined.append(col)
    return ClassifyNominalResponse(table=store.key, refined=refined, n=len(refined))


@tool(desk="analytics")
def combine_columns(
    table: str, col_a: str, col_b: str, op: str, name: str | None = None
) -> AnalysisResultResponse:
    """New feature from two numeric columns: add, subtract, multiply, divide or ratio.
    Workspace tables only."""
    return _result(feature_computation.combine_columns(_store(table), col_a, col_b, op, name))


@tool(desk="analytics")
def transform_column(
    table: str, column: str, func: str, name: str | None = None
) -> AnalysisResultResponse:
    """Math transform of one column (log/log1p/sqrt/square/reciprocal/abs/zscore) into
    a new feature column. Workspace tables only."""
    return _result(feature_computation.transform_column(_store(table), column, func, name))


@tool(desk="analytics")
def bin_column(
    table: str, column: str, n_bins: int = 4, strategy: str = "quantile", name: str | None = None
) -> AnalysisResultResponse:
    """Discretize a numeric column into ordinal bins (quantile or uniform).
    Workspace tables only."""
    return _result(feature_computation.bin_column(_store(table), column, n_bins, strategy, name))


@tool(desk="analytics")
def expand_datetime(
    table: str, column: str, parts: list[str] | None = None
) -> AnalysisResultResponse:
    """Expand a datetime column into calendar-part feature columns.
    Workspace tables only."""
    return _result(feature_computation.expand_datetime(_store(table), column, parts))


@tool(desk="analytics")
def group_aggregate(
    table: str,
    group_by: str,
    value: str,
    agg: str = "mean",
    name: str | None = None,
    add_deviation: bool = False,
) -> AnalysisResultResponse:
    """Per-group statistic broadcast back to every row, optionally with each row's
    deviation from its group. Workspace tables only."""
    return _result(
        feature_computation.group_aggregate(
            _store(table), group_by, value, agg, name, add_deviation
        )
    )


@tool(desk="analytics")
def row_aggregate(
    table: str, columns: list[str], agg: str = "sum", name: str | None = None
) -> AnalysisResultResponse:
    """Row-wise aggregate (sum/mean/min/max) across several numeric columns.
    Workspace tables only."""
    return _result(feature_computation.row_aggregate(_store(table), columns, agg, name))


@tool(desk="analytics")
def normalize_fractions(
    table: str, columns: list[str], suffix: str = "_frac"
) -> AnalysisResultResponse:
    """Turn a set of count columns into per-row fractions summing to 1.
    Workspace tables only."""
    return _result(feature_computation.normalize_fractions(_store(table), columns, suffix))


@tool(desk="analytics")
def compute_feature(table: str, name: str, expression: str) -> AnalysisResultResponse:
    """One new column from a single Postgres scalar expression over the table's
    columns (e.g. `clicks::float / NULLIF(impressions, 0)`). No subqueries, DDL or
    file access. Workspace tables only."""
    return _result(feature_computation.compute_feature(_store(table), name, expression))


@tool(desk="analytics")
def cluster(table: str, n_clusters: int | None = None) -> AnalysisResultResponse:
    """K-means over the table's features (k auto-picked by silhouette when omitted);
    writes a `cluster` label column back. Workspace tables only."""
    return _result(clustering.cluster(_store(table), n_clusters))


@tool(desk="analytics")
def profile_clusters(table: str) -> AnalysisResultResponse:
    """Characterize each cluster (sizes, numeric means, dominant categories).
    Requires cluster() to have run on the table."""
    return _result(clustering.profile_clusters(_store(table)))


@tool(desk="analytics")
def reduce_dimensions(
    table: str, method: str = "pca", n_components: int = 2
) -> AnalysisResultResponse:
    """PCA/t-SNE/UMAP projection written back as component columns.
    Workspace tables only."""
    return _result(dimreduction.reduce_dimensions(_store(table), method, n_components))


def _train(
    table: str, target: str, name: str | None, task: str, backend: str
) -> AnalysisResultResponse | TrainedModelResponse:
    store = _store(table)
    model_name = name or target
    if task == "classification":
        model = supervised.train_classifier(store, target, backend=backend)
    else:
        model = supervised.train_regressor(store, target, backend=backend)
    if isinstance(model, Result):
        return _result(model)
    model_store.save_model(current(), model_name, model)
    return TrainedModelResponse(
        model_name=model_name,
        table=store.key,
        target=target,
        task=task,
        backend=backend,
        features=list(model._feature_names),
    )


@tool(desk="analytics")
def train_classifier(
    table: str, target: str, name: str | None = None, backend: str = "gbt"
) -> AnalysisResultResponse | TrainedModelResponse:
    """Train and persist a classifier on the table (default gradient-boosted trees)."""
    return _train(table, target, name, "classification", backend)


@tool(desk="analytics")
def train_regressor(
    table: str, target: str, name: str | None = None, backend: str = "gbt"
) -> AnalysisResultResponse | TrainedModelResponse:
    """Train and persist a regressor on the table (default gradient-boosted trees)."""
    return _train(table, target, name, "regression", backend)


@tool(desk="analytics")
def evaluate(model_name: str) -> AnalysisResultResponse:
    """Evaluate a trained model on its held-out test split."""
    return _result(supervised.evaluate(None, model_store.load_model(current(), model_name)))


@tool(desk="analytics")
def feature_importance(model_name: str) -> AnalysisResultResponse:
    """Permutation feature importance for a trained model, mapped to source columns."""
    return _result(interpretation.feature_importance(model_store.load_model(current(), model_name)))


@tool(desk="analytics")
def add_predictions(
    table: str, model_name: str, column_name: str | None = None
) -> AnalysisResultResponse:
    """Write a trained model's predictions onto the table as a new column.
    Workspace tables only."""
    store = _store(table)
    model = model_store.load_model(current(), model_name)
    frame = store.get_frame()
    preds = model.predict(frame[model._feature_names])
    col = column_name or f"{model_name}_pred"
    store.write_back_column(col, list(preds))
    return _result(
        Result(
            method="add_predictions",
            summary=f"Wrote {len(preds)} predictions to column {col!r}",
            values={"column": col, "n": len(preds)},
            metadata={"model": model_name, "table": store.key},
        )
    )


@tool(desk="analytics")
def explain_prediction(table: str, model_name: str, row_index: int = 0) -> AnalysisResultResponse:
    """SHAP explanation for one row's prediction; row_index is 0-based in the
    table's stable order."""
    store = _store(table)
    model = model_store.load_model(current(), model_name)
    row = store.get_frame().iloc[int(row_index)].to_dict()
    return _result(interpretation.explain_prediction(model, row))


@tool(desk="analytics")
def decompose(table: str, time_column: str, value_column: str) -> AnalysisResultResponse:
    """Split a time series into trend, seasonality and residual."""
    return _result(timeseries.decompose(_store(table), time_column, value_column))


@tool(desk="analytics")
def forecast(
    table: str, time_column: str, value_column: str, horizon: int = 10
) -> AnalysisResultResponse:
    """ARIMA point forecasts with 95% confidence intervals."""
    return _result(timeseries.forecast(_store(table), time_column, value_column, horizon))


@tool(desk="analytics")
def detect_changepoints(
    table: str, time_column: str, value_column: str, penalty: float = 10.0
) -> AnalysisResultResponse:
    """Detect regime shifts in a time series (PELT); returns change times and
    per-segment means."""
    return _result(
        timeseries.detect_changepoints(_store(table), time_column, value_column, penalty)
    )


@tool(desk="analytics")
def explain_metric(table: str, target: str, max_depth: int = 3) -> AnalysisResultResponse:
    """Ranked drivers of a metric plus readable segment rules from a shallow
    decision tree."""
    return _result(insights.explain_metric(_store(table), target, max_depth))


@tool(desk="analytics")
def market_basket(
    table: str,
    transaction_column: str,
    item_column: str,
    min_support: float = 0.01,
    min_confidence: float = 0.2,
    max_rules: int = 50,
) -> AnalysisResultResponse:
    """Association-rule mining over transaction/item pairs, ranked by lift."""
    return _result(
        basket.market_basket(
            _store(table), transaction_column, item_column, min_support, min_confidence, max_rules
        )
    )


@tool(desk="analytics")
def causal_effect(
    table: str, treatment: str, outcome: str, confounders: list[str] | None = None
) -> AnalysisResultResponse:
    """Backdoor-adjusted causal effect estimate with refutation (DoWhy)."""
    return _result(causal.causal_effect(_store(table), treatment, outcome, confounders))


@tool(desk="analytics")
def rfm(
    table: str, customer_column: str, date_column: str, monetary_column: str
) -> AnalysisResultResponse:
    """RFM quintile segmentation with named segments."""
    return _result(cohort.rfm(_store(table), customer_column, date_column, monetary_column))


@tool(desk="analytics")
def retention_cohorts(table: str, customer_column: str, date_column: str) -> AnalysisResultResponse:
    """Monthly retention matrix: first-activity cohort by months since."""
    return _result(cohort.retention_cohorts(_store(table), customer_column, date_column))


@tool(desk="analytics")
def compare_periods(
    table: str, time_column: str, value_column: str, split: str | None = None
) -> AnalysisResultResponse:
    """Before-vs-after comparison around a cut date (default median): means, change,
    significance."""
    return _result(compare.compare_periods(_store(table), time_column, value_column, split))
