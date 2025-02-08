# app/core/events/py
import uuid
import logging
import asyncio

from typing import Callable, Dict, List, Any

logger = logging.getLogger(__name__)

class EventEmitter:
    _instance = None
    _handlers: Dict[str, List[Callable]] = {}
    _response_handlers: Dict[str, asyncio.Future] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._handlers = {}
            cls._instance._response_handlers = {}
        return cls._instance
    
    def on(self, event: str, handler: Callable):
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)
    
    async def emit(self, event: str, data: Any) -> Any:
        response_event = f"{event}:response:{uuid.uuid4()}"
        # 創建一個新的 Future 來等待回應
        future = asyncio.Future()
        self._response_handlers[response_event] = future
        
        logger.info(f"Emitting event: {event}")
        message = {
            "data": data,
            "response_event": response_event
        }
        
        if event in self._handlers:
            await asyncio.gather(
                *[handler(message) for handler in self._handlers[event]]
            )
            
        try:
            response = await asyncio.wait_for(future, timeout=5)
            logger.info(f"Received response for event: {event}")
            return response
        finally:
            self._response_handlers.pop(response_event, None)
        
    async def emit_response(self, response_event: str, response_message: Any):
        if response_event in self._response_handlers:
            future = self._response_handlers[response_event]
            if not future.done():
                future.set_result(response_message)