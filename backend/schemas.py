"""Scheme Pydantic pentru endpoint-urile backend."""

from typing import Optional

from pydantic import BaseModel


class MessageSchema(BaseModel):
    message: str


class StatusSchema(BaseModel):
    status: str


class RateSchema(BaseModel):
    id: int
    date: str
    currency: str
    value: float
    created_at: str


class ForecastSchema(BaseModel):
    id: Optional[int] = None
    forecast_date: Optional[str] = None
    currency: Optional[str] = None
    predicted_value: Optional[float] = None
    model_name: Optional[str] = None
    mae_14_days: Optional[float] = None
    created_at: Optional[str] = None
    message: Optional[str] = None

    class Config:
        extra = "allow"


class RunSchema(BaseModel):
    id: int
    model_name: str
    parameters_json: Optional[str] = None
    mae: Optional[float] = None
    rmse: Optional[float] = None
    mape: Optional[float] = None
    created_at: str
