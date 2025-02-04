# api.py
from fastapi import FastAPI, HTTPException
from models import StrategyMetadata, StrategyCreate, StrategyUpdate
from manager import StrategyManager
from typing import List
import uuid

app = FastAPI()
manager = StrategyManager()

@app.post("/strategies", response_model=StrategyMetadata)
def add_strategy(strategy: StrategyCreate):
    strategy_id = str(uuid.uuid4())
    strategy_data = {
        "id": strategy_id,
        **strategy.model_dump()
    }
    try:
        return manager.add_strategy(strategy_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/strategies", response_model=List[StrategyMetadata])
def list_strategies():
    return manager.list_strategies()

@app.get("/strategies/{strategy_id}", response_model=StrategyMetadata)
def get_strategy(strategy_id: str):
    strategy = manager.get_strategy(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy

@app.patch("/strategies/{strategy_id}/pause", response_model=StrategyMetadata)
def pause_strategy(strategy_id: str):
    strategy = manager.pause_strategy(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy

@app.patch("/strategies/{strategy_id}/resume", response_model=StrategyMetadata)
def resume_strategy(strategy_id: str):
    strategy = manager.resume_strategy(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy

@app.put("/strategies/{strategy_id}", response_model=StrategyMetadata)
def modify_strategy(strategy_id: str, strategy: StrategyUpdate):
    updated = manager.update_strategy(strategy_id, strategy.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return updated

@app.delete("/strategies/{strategy_id}")
def remove_strategy(strategy_id: str):
    if not manager.remove_strategy(strategy_id):
        raise HTTPException(status_code=404, detail="Strategy not found")
    return {"message": "Strategy removed successfully"}