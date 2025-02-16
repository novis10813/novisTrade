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
    field_serializer,
    model_serializer
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
    
ProcessSteps = Dict[str, List[PreprocessStep]]
PreprocessConfig = Dict[str, ProcessSteps]


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
    inactive = "inactive"
    active = "active"
    paused = "paused"
    error = "error"
    
# 用於創建模型
class StrategyMetadataBase(BaseModel):
    name: str
    description: Optional[str] = None
    data: DataConfig
    preprocess: PreprocessConfig
    signals: SignalConfig
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            StrategyStatus: lambda v: v.value,
        }
    )
    
    
class StrategyMetadataCreate(StrategyMetadataBase):
    """Model for creation (input from client)"""
    pass

    # @model_validator(mode="after")
    # def validate_preprocess_keys(cls, values):
    #     data_keys = {dt.key() for dt in values["data"]["types"]}
    #     preprocess_keys = set(values["preprocess"].keys())

    #     unused_keys = preprocess_keys - data_keys
    #     if unused_keys:
    #         warnings.warn(
    #             f"The following data sources are subscribed but not used in preprocess: {unused_keys}"
    #         )

class StrategyMetadataCreateResponse(BaseModel):
    """Model for creation response"""
    message: str
    id: str

class StrategyMetadataInDB(StrategyMetadataBase):
    """Model for storage (in DB)
    說明:
    1. client 建立新策略後第一步，會先把模型存到 DB 中
    2. 接著會把模型載入到 Redis 中
    所以 StrategyMetadata 會繼承 StrategyMetadataInDB
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    

class StrategyMetadataRuntime(StrategyMetadataInDB):
    """Runtime model including status
    說明:
    策略載入 Redis 後，會需要紀錄 runtime 的狀態，
    所以 StrategyMetadata 會繼承 StrategyMetadataInDB ，並且新增 status 欄位
    """
    status: StrategyStatus = Field(default=StrategyStatus.inactive)
    
    
# 完整更新模型
class StrategyMetadataUpdate(StrategyMetadataRuntime):
    """Model for update (input from client)"""
    pass

# Patch 模型

class DataConfigPatch(BaseModel):
    source: Optional[Literal["stream", "historic"]] = None
    types: Optional[List[DataType]] = None
    
class PreprocessConfigPatch(BaseModel):
    operation: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    
class SignalConfigPatch(BaseModel):
    models: Optional[List[SignalModel]] = None
    logic: Optional[SignalLogic] = None
        
class PreprocessStepPatch(BaseModel):
    operation: Optional[str] = None
    params: Optional[Dict[str, Any]] = None

# 使用 TypeVar 和 Dict 來定義可選的嵌套結構
ProcessStepsPatch = Dict[str, List[PreprocessStepPatch]]
PreprocessConfigPatch = Dict[str, ProcessStepsPatch]

class StrategyMetadataPatch(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[StrategyStatus] = None
    data: Optional[DataConfigPatch] = None
    preprocess: Optional[PreprocessConfigPatch] = None
    signals: Optional[SignalConfigPatch] = None
    updated_at: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(
        extra = "forbid"
    )
    
# 用於回應的模型
class StrategyMetadataRuntimeSummary(BaseModel):
    id: str
    name: str
    description: str
    status: StrategyStatus
    
class StrategyMetadataRuntimeResponse(StrategyMetadataRuntime):
    pass

class StrategyMetadataDBSummary(BaseModel):
    id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime

class StrategyMetadataDBResponse(StrategyMetadataInDB):
    pass