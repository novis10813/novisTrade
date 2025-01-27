import asyncio
import websockets
from typing import Dict, Set, Any
import logging
from dataclasses import dataclass
from datetime import datetime

import websockets.asyncio
import websockets.asyncio.client

@dataclass
class WebSocketConnection:
    """WebSocket 連接資訊"""
    ws: websockets.asyncio.client.ClientConnection
    uri: str
    created_at: datetime
    closed: bool = False

class WebSocketManager:
    """ 基礎的 WebSocket 連線管理器，負責處理：
    - WebSocket 連線的建立和管理
    - 訊息的接收和發送
    - 錯誤處理和重連邏輯
    """
    def __init__(self, level: int = logging.INFO):
        self.connections: Dict[str, WebSocketConnection] = {}
        self._connection_locks: Dict[str, asyncio.Lock] = {}
        self.running = True
        self.message_callback = None
        self.main_task = None
        self._connection_updates = asyncio.Queue()
        self._update_event = asyncio.Event()
        self._active_tasks: Set[asyncio.Task] = set()
        self.ACTION_ADD = "add"
        self.ACTION_REMOVE = "remove"
        self.ACTION_RECONNECT = "reconnect"
        self.ACTION_SEND = "send"
        
        self._setup_logger(level=level)
        
    def _setup_logger(self, level: int = logging.INFO):
        """設置 Logger 等級"""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(level)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)

    async def start(self):
        """啟動主要接收循環"""
        if self.main_task is None or self.main_task.done():
            self.running = True
            self.main_task = asyncio.create_task(self._main_receive_loop())
            self.logger.info("Started main receive loop")

    def _create_task(self, coro) -> asyncio.Task:
        """創建任務並追蹤它"""
        task = asyncio.create_task(coro)
        self._active_tasks.add(task)
        task.add_done_callback(self._active_tasks.discard)
        return task
            
    async def _main_receive_loop(self):
        """事件驅動的主循環"""
        while self.running:
            tasks = set()

            # 處理連接更新，這邊他是獨立的任務
            if not self._connection_updates.empty():
                update_task = self._create_task(self._process_updates())

            # 添加活動連接的接收任務
            active_connections = {
                conn_id: conn for conn_id, conn in self.connections.items()
                if not conn.closed
            }

            # 為每個活動連接創建接收任務
            for conn_id in active_connections:
                tasks.add(self._create_task(self._receive_message(conn_id)))

            if not tasks and not update_task:
                # 如果沒有任務，等待新的事件
                self.logger.debug("Waiting for events...")
                await self._update_event.wait()
                self._update_event.clear()
                continue
            
            if update_task:
                try:
                    await update_task
                except Exception as e:
                    self.logger.error(f"Error processing updates: {e}")
                    
            # 等待任何一個任務完成
            if tasks:
                try:
                    done, pending = await asyncio.wait(
                        tasks,
                        return_when=asyncio.FIRST_COMPLETED,
                    )

                    # 處理完成的任務的結果（包括異常）
                    for task in done:
                        try:
                            await task
                        except Exception as e:
                            self.logger.error(f"Task error: {e}")

                    # 取消剩餘的任務
                    for task in pending:
                        task.cancel()

                except Exception as e:
                    self.logger.error(f"Error in main loop: {e}")
                    await asyncio.sleep(1)

    async def _process_updates(self):
        """處理連接更新佇列"""
        try:
            while not self._connection_updates.empty():
                message: Dict[str, Any] = await self._connection_updates.get()
                conn_id: str = message.get("connection_id")
                try:
                    match message:
                        case {"action": self.ACTION_ADD}:
                            await self._handle_add(conn_id, message["uri"], message.get("ready"))
                            
                        case {"action": self.ACTION_REMOVE}:
                            await self._handle_remove(conn_id)
                            
                        case {"action": self.ACTION_RECONNECT}:
                            await self._handle_reconnect(conn_id)
                            
                        case {"action": self.ACTION_SEND}:
                            await self._handle_send(conn_id, message["message"], message.get("sent"))
                            
                except Exception as e:
                    self.logger.error(f"Error processing message {message}: {e}")
                finally:
                    self._connection_updates.task_done()
        except Exception as e:
            self.logger.error(f"Error processing updates: {e}")

    async def _receive_message(self, connection_id: str):
        """從單個 WebSocket 接收消息"""
        if connection_id not in self.connections or self.connections[connection_id].closed:
            return

        conn = self.connections[connection_id]
        try:
            message = await conn.ws.recv()
            if self.message_callback:
                await self.message_callback(connection_id, message)
        except websockets.exceptions.ConnectionClosed:
            if not conn.closed:
                self.logger.info(f"Connection closed for {connection_id}")
                await self.reconnect(connection_id)
        except Exception as e:
            self.logger.error(f"Error receiving from {connection_id}: {e}")
            if not conn.closed:
                await self.remove_connection(connection_id)
                
    def _get_connection_lock(self, connection_id: str) -> asyncio.Lock:
        if connection_id not in self._connection_locks:
            self._connection_locks[connection_id] = asyncio.Lock()
        return self._connection_locks[connection_id]

    async def add_connection(self, uri: str, connection_id: str) -> str:
        """添加新的 WebSocket 連接"""
        async with self._get_connection_lock(connection_id):
            connection_ready = asyncio.Future()
            await self._connection_updates.put({
                "action": self.ACTION_ADD,
                "connection_id": connection_id,
                "uri": uri,
                "ready": connection_ready
            })
            self._update_event.set()
            # 等待連接建立完成
            await connection_ready
            return connection_id
        
    async def _handle_add(self, connection_id: str, uri: str, ready: asyncio.Future):
        try:
            self.logger.info(f"Connecting to {uri} with ID {connection_id}")
            ws = await websockets.asyncio.client.connect(uri)
            self.logger.info(f"Successfully connected to {uri} with ID {connection_id}")
            
            self.connections[connection_id] = WebSocketConnection(
                ws=ws,
                uri=uri,
                created_at=datetime.now(),
                closed=False
            )
            
            if ready and not ready.done():
                ready.set_result(True)
        except asyncio.TimeoutError:
            self.logger.error(f"Connection to {uri} timed out")
            if ready and not ready.done():
                ready.set_exception(TimeoutError("Connection timed out"))
                
        except Exception as e:
            self.logger.error(f"Error connecting to {uri}: {e}")
            if ready and not ready.done():
                ready.set_exception(e)

    async def remove_connection(self, connection_id: str) -> None:
        """移除指定的 WebSocket 連接"""
        async with self._get_connection_lock(connection_id):
            await self._connection_updates.put({
                "action": "remove",
                "connection_id": connection_id
            })
            self._update_event.set()
            return None
        
    async def _handle_remove(self, connection_id: str) -> None:
        if connection_id not in self.connections:
            return
        
        try:
            conn = self.connections[connection_id]
            if conn.closed:
                return
            conn.closed = True
            del self.connections[connection_id]
            self._create_task(self._close_websocket(conn.ws))
            self.logger.info(f"Successfully removed connection {connection_id}")
        except Exception as e:
            self.logger.error(f"Error removing connection {connection_id}: {e}")

    async def reconnect(self, connection_id: str) -> None:
        """重新建立指定的連線
        
        目前的作法是等到連線關閉後才重新連線。之後可以改成 hot swap 的方式。
        """
        async with self._get_connection_lock(connection_id):
            await self._connection_updates.put({
                "action": "reconnect",
                "connection_id": connection_id
            })
            self._update_event.set()
            return None
            
    async def _close_websocket(self, ws: websockets.asyncio.client.ClientConnection) -> None:
        """關閉 WebSocket 連接"""
        try:
            await ws.close()
        except Exception as e:
            self.logger.error(f"Error closing WebSocket: {e}")
            
        
    async def _handle_reconnect(self, connection_id: str) -> None:
        if connection_id not in self.connections:
            raise ValueError(f"Connection {connection_id} not found")
        
        conn = self.connections[connection_id]
        new_ws = await websockets.asyncio.client.connect(conn.uri)
        old_ws = conn.ws
        conn.ws = new_ws
        conn.closed = False
        conn.created_at = datetime.now()
        self._create_task(self._close_websocket(old_ws))
        if self.reconnect_callback:
            await self.reconnect_callback(connection_id)
            
        self.logger.info(f"Successfully reconnected {connection_id}")

    def set_message_callback(self, callback):
        """設置消息回調函數"""
        self.message_callback = callback
        
    def set_reconnect_callback(self, callback):
        """設置重連回調函數"""
        self.reconnect_callback = callback

    async def send_message(self, connection_id: str, message: str) -> None:
        """向指定的 WebSocket 發送消息"""
        async with self._get_connection_lock(connection_id):
            message_sent = asyncio.Future()
            await self._connection_updates.put({
                "action": self.ACTION_SEND,
                "connection_id": connection_id,
                "message": message,
                "sent": message_sent
            })
            self._update_event.set()
            await message_sent
            
    async def _handle_send(self, connection_id: str, message: str, message_sent: asyncio.Future) -> None:
        if connection_id not in self.connections:
            raise ValueError(f"Connection {connection_id} not found")
        
        conn = self.connections[connection_id]
        if conn.closed:
            raise ValueError(f"Connection {connection_id} is closed")
        try:
            await conn.ws.send(message)
            self.logger.debug(f"Sent message to {connection_id}: {message}")
            if message_sent and not message_sent.done():
                message_sent.set_result(True)
        except Exception as e:
            self.logger.error(f"Error sending message to {connection_id}: {e}")
            if message_sent and not message_sent.done():
                message_sent.set_exception(e)
            await self.remove_connection(connection_id)

    async def close(self) -> None:
        """關閉所有連接及主循環"""
        self.running = False
        self._update_event.set()

        # 取消所有活動任務
        for task in self._active_tasks:
            task.cancel()

        # 等待所有任務完成
        if self._active_tasks:
            await asyncio.gather(*self._active_tasks, return_exceptions=True)

        # 關閉所有連接
        for conn_id in list(self.connections.keys()):
            if not self.connections[conn_id].closed:
                await self.remove_connection(conn_id)

    def get_connection_info(self) -> Dict[str, dict]:
        """獲取所有連接的資訊"""
        return {
            conn_id: {
                "uri": conn.uri,
                "created_at": conn.created_at.isoformat(),
                "is_connected": not conn.closed
            }
            for conn_id, conn in self.connections.items()
        }