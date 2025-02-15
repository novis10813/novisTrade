import uuid
import warnings

from enum import Enum
from datetime import datetime
from typing import Dict, Any, Optional, List, Literal
from pydantic import (
    BaseModel, 
    Field, 
    model_validator, 
    RootModel, 
    ConfigDict, 
    field_serializer
)


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


class StrategyStatus(str, Enum):
    created = "created"
    active = "active"
    paused = "paused"
    stopped = "stopped"
    error = "error"
    
# 用於創建模型
class StrategyMetadata(BaseModel):
    name: str
    description: Optional[str] = None
    status: StrategyStatus = StrategyStatus.created
    data: DataConfig
    preprocess: Dict[str, PreprocessConfig]
    signals: SignalConfig

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            StrategyStatus: lambda v: v.value,
        }
    )
    
    
class StrategyMetadataCreate(BaseModel):
    name: str
    description: Optional[str] = None
    status: StrategyStatus = StrategyStatus.created
    data: DataConfig
    preprocess: Dict[str, PreprocessConfig]
    signals: SignalConfig

    # @model_validator(mode="after")
    # def validate_preprocess_keys(cls, values):
    #     data_keys = {dt.key() for dt in values["data"]["types"]}
    #     preprocess_keys = set(values["preprocess"].keys())

    #     unused_keys = preprocess_keys - data_keys
    #     if unused_keys:
    #         warnings.warn(
    #             f"The following data sources are subscribed but not used in preprocess: {unused_keys}"
    #         )

# 完整更新模型
class StrategyMetadataUpdate(StrategyMetadata):
    pass

# 部分更新模型
class StrategyMetadataPatch(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[Literal["active", "paused", "stopped"]] = None
    data: Optional[DataConfig] = None
    preprocess: Optional[Dict[str, PreprocessConfig]] = None
    signals: Optional[SignalConfig] = None
    
# 用於回應的模型
class StrategyMetadataResponse(BaseModel):
    name: str
    description: str
    
class StrategyMetadataCreateResponse(BaseModel):
    message: str
    id: str
    
class StrategyMetadataInDB(StrategyMetadata):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)