import uuid
import warnings

from pydantic import BaseModel, Field, model_validator, RootModel
from typing import Dict, Any, Optional, List, Literal
from datetime import datetime


class DataType(BaseModel):
    exchange: str
    market: Literal["spot", "perp", "coin"]
    symbol: str
    stream: str

    def key(self) -> str:
        """生成用于 preprocess 的唯一 key"""
        return f"{self.exchange}:{self.market}:{self.symbol}:{self.stream}"


class DataConfig(BaseModel):
    source: Literal["stream", "historic"]
    types: List[DataType]  # list of different data sources


class PreprocessStep(BaseModel):
    operation: str
    params: Dict[str, Any]


class PreprocessConfig(RootModel[Dict[str, List[PreprocessStep]]]):
    pass


class SignalModel(BaseModel):
    model_id: str
    file_name: str
    input_features: List[str]
    should_wait: bool = True


class SignalLogic(BaseModel):
    long_entry: str
    long_exit: str
    short_entry: str
    short_exit: str


class SignalConfig(BaseModel):
    models: List[SignalModel]
    logic: SignalLogic


class StrategyMetadata(BaseModel):
    name: str
    description: Optional[str] = None
    status: Literal["active", "paused", "stopped"] = "stopped"
    data: DataConfig
    preprocess: Dict[str, PreprocessConfig]
    signals: SignalConfig
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}}

    # @model_validator(mode="after")
    # def validate_preprocess_keys(cls, values):
    #     data_keys = {dt.key() for dt in values["data"]["types"]}
    #     preprocess_keys = set(values["preprocess"].keys())

    #     unused_keys = preprocess_keys - data_keys
    #     if unused_keys:
    #         warnings.warn(
    #             f"The following data sources are subscribed but not used in preprocess: {unused_keys}"
    #         )


class StrategyMetadataWithId(StrategyMetadata):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

# 用於請求的模型
class StrategyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any]


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None

