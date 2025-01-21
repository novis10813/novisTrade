import asyncio
import websockets
from typing import Dict, Set
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
    reconnect_interval: float = 23.5 * 3600  # 預設24小時重連

class WebSocketManager:
    """ 基礎的 WebSocket 連線管理器，負責處理：
    - WebSocket 連線的建立和管理
    - 訊息的接收和發送
    - 錯誤處理和重連邏輯
    """
    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self.logger = logging.getLogger(__name__)
        self.running = True
        self.message_callback = None
        self.main_task = None
        self._connection_updates = asyncio.Queue()
        self._update_event = asyncio.Event()
        self._active_tasks: Set[asyncio.Task] = set()
        self._reconnect_task = None

    async def start(self):
        """啟動主要接收循環"""
        if self.main_task is None or self.main_task.done():
            self.running = True
            self.main_task = asyncio.create_task(self._main_receive_loop())
            self._reconnect_task = asyncio.create_task(self._check_reconnect())
            self.logger.info("Started main receive loop")

    def _create_task(self, coro) -> asyncio.Task:
        """創建任務並追蹤它"""
        task = asyncio.create_task(coro)
        self._active_tasks.add(task)
        task.add_done_callback(self._active_tasks.discard)
        return task
    
    async def _check_reconnect(self):
        """檢查並執行重連的監控任務"""
        while self.running:
            try:
                current_time = datetime.now()
                for conn_id, conn in list(self.connections.items()):
                    if not conn.closed:
                        elapsed_time = (current_time - conn.created_at).total_seconds()
                        if elapsed_time >= conn.reconnect_interval:
                            self.logger.info(f"Connection {conn_id} needs reconnection after {elapsed_time} seconds")
                            await self.reconnect(conn_id)
            except Exception as e:
                self.logger.error(f"Error in reconnect monitor: {e}")
            
            await asyncio.sleep(1)  # 每秒檢查一次
            
    async def reconnect(self, connection_id: str):
        """重新建立指定的連線"""
        if connection_id not in self.connections:
            raise ValueError(f"Connection {connection_id} not found")

        conn = self.connections[connection_id]
        uri = conn.uri
        reconnect_interval = conn.reconnect_interval

        try:
            # 先移除舊連線
            await self.remove_connection(connection_id)
            
            # 重新建立連線
            await self.add_connection(
                uri=uri,
                connection_id=connection_id,
                reconnect_interval=reconnect_interval
            )
            
            self.logger.info(f"Successfully reconnected {connection_id}")
        except Exception as e:
            self.logger.error(f"Failed to reconnect {connection_id}: {e}")

    async def _main_receive_loop(self):
        """事件驅動的主循環"""
        while self.running:
            tasks = set()

            # 處理連接更新
            if not self._connection_updates.empty():
                tasks.add(self._create_task(self._process_updates()))

            # 添加活動連接的接收任務
            active_connections = {
                conn_id: conn for conn_id, conn in self.connections.items()
                if not conn.closed
            }

            # 為每個活動連接創建接收任務
            for conn_id in active_connections:
                tasks.add(self._create_task(self._receive_message(conn_id)))

            if not tasks:
                # 如果沒有任務，等待新的事件
                self.logger.debug("Waiting for events...")
                await self._update_event.wait()
                self._update_event.clear()
                continue

            # 等待任何一個任務完成
            try:
                done, pending = await asyncio.wait(
                    tasks,
                    return_when=asyncio.FIRST_COMPLETED
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
                conn_id, action = await self._connection_updates.get()
                if action == "remove" and conn_id in self.connections:
                    self.connections[conn_id].closed = True
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
                await self.remove_connection(connection_id)
        except Exception as e:
            self.logger.error(f"Error receiving from {connection_id}: {e}")
            if not conn.closed:
                await self.remove_connection(connection_id)

    async def add_connection(self, uri: str, connection_id: str, reconnect_interval: float = 23.5 * 3600) -> str:
        """添加新的 WebSocket 連接"""
        if connection_id in self.connections:
            await self.remove_connection(connection_id)

        try:
            ws = await websockets.asyncio.client.connect(uri)
            self.connections[connection_id] = WebSocketConnection(
                ws=ws,
                uri=uri,
                created_at=datetime.now(),
                closed=False,
                reconnect_interval=reconnect_interval
            )

            await self._connection_updates.put((connection_id, "add"))
            self._update_event.set()

            self.logger.info(f"Successfully connected to {uri} with ID {connection_id}")
            return connection_id

        except Exception as e:
            self.logger.error(f"Failed to connect to {uri}: {e}")
            raise

    async def remove_connection(self, connection_id: str) -> bool:
        """移除指定的 WebSocket 連接"""
        if connection_id not in self.connections:
            return False

        conn = self.connections[connection_id]
        if conn.closed:
            return False

        try:
            await self._connection_updates.put((connection_id, "remove"))
            self._update_event.set()

            await conn.ws.close()
            conn.closed = True
            del self.connections[connection_id]
            self.logger.info(f"Successfully removed connection {connection_id}")
            return True

        except Exception as e:
            conn.closed = True
            if connection_id in self.connections:
                del self.connections[connection_id]
            return False

    def set_message_callback(self, callback):
        """設置消息回調函數"""
        self.message_callback = callback

    async def send_message(self, connection_id: str, message: str) -> None:
        """向指定的 WebSocket 發送消息"""
        if connection_id not in self.connections:
            raise ValueError(f"Connection {connection_id} not found")

        conn = self.connections[connection_id]
        if not conn.closed:
            await conn.ws.send(message)

    async def close(self) -> None:
        """關閉所有連接及主循環"""
        self.running = False
        self._update_event.set()
        
        if self._reconnect_task:
            self._reconnect_task.cancel()

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