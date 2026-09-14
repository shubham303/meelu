from typing import Any

from pydantic import BaseModel, Field

from src.data_analytics.shared import honesty
from src.data_analytics.shared.honesty import Trust
from src.data_analytics.shared.results import Result
from src.data_analytics.shared.serialize import jsonable


class AnalysisResultResponse(BaseModel):
    method: str
    summary: str
    trust: Trust
    declined: bool
    values: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_result(cls, res: Result) -> "AnalysisResultResponse":
        trust = res.trust or honesty.unassessed()
        return cls(
            method=res.method,
            summary=res.summary,
            trust=trust,
            declined=trust.declined,
            values=jsonable(res.values),
            metadata=jsonable(res.metadata),
        )


class UnclassifiedColumn(BaseModel):
    column: str
    distinct: int
    sample: list[str]


class CategoricalColumnsResponse(BaseModel):
    table: str
    unclassified: list[UnclassifiedColumn]
    n: int


class ColumnTypeResponse(BaseModel):
    table: str
    column: str
    type: str


class ColumnTypeClearedResponse(BaseModel):
    table: str
    column: str
    cleared: bool = True


class ClassifyNominalResponse(BaseModel):
    table: str
    refined: list[str]
    n: int


class TrainedModelResponse(BaseModel):
    model_name: str
    table: str
    target: str
    task: str
    backend: str
    features: list[str]
