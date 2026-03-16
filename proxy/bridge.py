"""
Traffic bridge between client and Telegram.
"""

import asyncio
import logging
from typing import Optional

from .config import settings
from .websocket import RawWebSocket, WebSocketError
from .mtproto import MTProtoSplitter, is_http_transport

logger = logging.getLogger(__name__)


class Bridge:
    """Bridge traffic between client and Telegram backend"""
    
    def __init__(self, pool):
        self.pool = pool
        self._recv_buf = settings.recv_buf_size
        self._send_buf = settings.send_buf_size
    
    async def bridge_websocket(
        self,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
        ws: RawWebSocket
    ):
        """Bridge traffic through WebSocket"""
        
        async def client_to_ws():
            """Client -> WebSocket"""
            try:
                while True:
                    data = await client_reader.read(self._recv_buf)
                    if not data:
                        break
                    await ws.send(data)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.debug(f"Client to WS error: {e}")
        
        async def ws_to_client():
            """WebSocket -> Client"""
            try:
                while True:
                    data = await ws.recv()
                    if not data:
                        break
                    client_writer.write(data)
                    await client_writer.drain()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.debug(f"WS to client error: {e}")
        
        # Run both directions concurrently
        try:
            await asyncio.gather(
                client_to_ws(),
                ws_to_client(),
                return_exceptions=True
            )
        except asyncio.CancelledError:
            pass
        finally:
            # Return connection to pool
            await self.pool.put(ws)
    
    async def bridge_tcp(
        self,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
        host: str,
        port: int
    ):
        """Bridge traffic through direct TCP (fallback)"""
        
        try:
            # Connect to target
            target_reader, target_writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=10.0
            )
        except Exception as e:
            logger.error(f"Failed to connect to {host}:{port}: {e}")
            return
        
        try:
            # Pipe in both directions
            await asyncio.gather(
                self._pipe(client_reader, target_writer),
                self._pipe(target_reader, client_writer),
                return_exceptions=True
            )
        finally:
            target_writer.close()
            try:
                await target_writer.wait_closed()
            except Exception:
                pass
    
    async def _pipe(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ):
        """Pipe data from reader to writer"""
        try:
            while True:
                data = await reader.read(self._recv_buf)
                if not data:
                    break
                writer.write(data)
                await writer.drain()
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
    
    async def handle_telegram_connection(
        self,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
        dc_id: int,
        is_media: bool,
        init_data: Optional[bytes] = None
    ):
        """
        Handle connection to Telegram DC.
        Tries WebSocket first, falls back to TCP.
        """
        # Try to get WebSocket from pool
        ws = await self.pool.get(dc_id, is_media)
        
        if ws:
            logger.debug(f"Using pooled WebSocket for DC{dc_id}")
            
            # Send init data if present
            if init_data:
                await ws.send(init_data)
            
            # Bridge through WebSocket
            await self.bridge_websocket(client_reader, client_writer, ws)
        else:
            # Fallback to direct TCP
            logger.debug(f"Falling back to TCP for DC{dc_id}")
            
            target_ip = self.pool._dc_ips.get(dc_id)
            if not target_ip:
                logger.error(f"No IP for DC{dc_id}")
                return
            
            await self.bridge_tcp(client_reader, client_writer, target_ip, 443)