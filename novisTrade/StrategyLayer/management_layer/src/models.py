from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime


class StrategyStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    

class StrategyMetadata(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    status: StrategyStatus = StrategyStatus.ACTIVE
    parameters: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }
        
# 用於請求的模型
class StrategyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any]

class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None