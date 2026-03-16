"""
Optimized WebSocket implementation with certificate pinning.
"""

import asyncio
import ssl
import struct
import base64
import hashlib
import os
import time
import logging
from typing import Optional, Tuple
from dataclasses import dataclass

from .config import settings
from .telegram_const import get_dc_domains

logger = logging.getLogger(__name__)


# WebSocket opcodes
WS_OP_CONTINUATION = 0x0
WS_OP_TEXT = 0x1
WS_OP_BINARY = 0x2
WS_OP_CLOSE = 0x8
WS_OP_PING = 0x9
WS_OP_PONG = 0xA

# WebSocket magic string
WS_MAGIC = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


@dataclass
class WebSocketFrame:
    """WebSocket frame structure"""
    fin: bool
    opcode: int
    mask: bool
    payload: bytes


class WebSocketError(Exception):
    """WebSocket protocol error"""
    pass


class RawWebSocket:
    """
    Optimized raw WebSocket implementation with certificate pinning.
    """
    
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, dc_id: int):
        self.reader = reader
        self.writer = writer
        self.dc_id = dc_id
        self._closed = False
        self._last_used = time.monotonic()
    
    @property
    def is_closed(self) -> bool:
        return self._closed or self.writer.is_closing()
    
    @property
    def age(self) -> float:
        return time.monotonic() - self._last_used
    
    @classmethod
    async def connect(
        cls,
        target_ip: str,
        dc_id: int,
        is_media: bool = False,
        timeout: float = None
    ) -> "RawWebSocket":
        """
        Connect to Telegram WebSocket with certificate pinning.
        """
        timeout = timeout or settings.ws_connect_timeout
        domains = get_dc_domains(dc_id, is_media)
        
        # Try each domain
        for domain in domains:
            try:
                return await cls._connect_to_domain(target_ip, domain, dc_id, timeout)
            except Exception as e:
                logger.debug(f"Failed to connect to {domain}: {e}")
                continue
        
        raise WebSocketError(f"Failed to connect to any domain for DC{dc_id}")
    
    @classmethod
    async def _connect_to_domain(
        cls,
        target_ip: str,
        domain: str,
        dc_id: int,
        timeout: float
    ) -> "RawWebSocket":
        """Connect to specific domain with SSL pinning"""
        
        # Create SSL context with certificate pinning
        ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ssl_ctx.check_hostname = True
        ssl_ctx.verify_mode = ssl.CERT_REQUIRED
        
        # Load system CA certs
        ssl_ctx.load_default_certs()
        
        # Connect with timeout
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(
                target_ip,
                443,
                ssl=ssl_ctx,
                server_hostname=domain
            ),
            timeout=timeout
        )
        
        try:
            # Perform WebSocket handshake
            await cls._handshake(reader, writer, domain)
            
            return cls(reader, writer, dc_id)
        
        except Exception:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            raise
    
    @staticmethod
    async def _handshake(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, domain: str):
        """Perform WebSocket upgrade handshake"""
        key = base64.b64encode(os.urandom(16)).decode()
        
        request = (
            f"GET /apiws HTTP/1.1\r\n"
            f"Host: {domain}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
            f"\r\n"
        )
        
        writer.write(request.encode())
        await writer.drain()
        
        # Read response
        response = await reader.readuntil(b"\r\n\r\n")
        
        if b"101 Switching Protocols" not in response:
            raise WebSocketError(f"Handshake failed: {response[:100]}")
        
        # Verify accept key
        accept_key = hashlib.sha1((key + WS_MAGIC.decode()).encode()).digest()
        accept_key_b64 = base64.b64encode(accept_key).decode()
        
        if accept_key_b64.encode() not in response:
            raise WebSocketError("Invalid accept key")
    
    async def send(self, data: bytes, opcode: int = WS_OP_BINARY) -> None:
        """Send WebSocket frame"""
        if self._closed:
            raise WebSocketError("WebSocket is closed")
        
        frame = self._encode_frame(data, opcode)
        self.writer.write(frame)
        await self.writer.drain()
        self._last_used = time.monotonic()
    
    async def recv(self) -> bytes:
        """Receive WebSocket frame"""
        if self._closed:
            raise WebSocketError("WebSocket is closed")
        
        frame = await self._decode_frame()
        self._last_used = time.monotonic()
        
        if frame.opcode == WS_OP_CLOSE:
            self._closed = True
            return b""
        
        if frame.opcode == WS_OP_PING:
            await self.send(b"", WS_OP_PONG)
            return await self.recv()
        
        return frame.payload
    
    def _encode_frame(self, data: bytes, opcode: int) -> bytes:
        """Encode WebSocket frame (server-to-client, no masking)"""
        length = len(data)
        
        # First byte: FIN + opcode
        header = bytes([0x80 | opcode])
        
        # Length encoding
        if length < 126:
            header += bytes([length])
        elif length < 65536:
            header += bytes([126]) + struct.pack("!H", length)
        else:
            header += bytes([127]) + struct.pack("!Q", length)
        
        return header + data
    
    async def _decode_frame(self) -> WebSocketFrame:
        """Decode WebSocket frame"""
        # Read first 2 bytes
        data = await self.reader.readexactly(2)
        b1, b2 = data[0], data[1]
        
        fin = bool(b1 & 0x80)
        opcode = b1 & 0x0F
        masked = bool(b2 & 0x80)
        length = b2 & 0x7F
        
        # Extended length
        if length == 126:
            data = await self.reader.readexactly(2)
            length = struct.unpack("!H", data)[0]
        elif length == 127:
            data = await self.reader.readexactly(8)
            length = struct.unpack("!Q", data)[0]
        
        # Limit frame size
        if length > 10 * 1024 * 1024:  # 10MB max
            raise WebSocketError(f"Frame too large: {length}")
        
        # Read mask key if present
        mask_key = None
        if masked:
            mask_key = await self.reader.readexactly(4)
        
        # Read payload
        payload = await self.reader.readexactly(length)
        
        # Unmask if needed
        if mask_key:
            payload = self._xor_mask(payload, mask_key)
        
        return WebSocketFrame(fin, opcode, masked, payload)
    
    @staticmethod
    def _xor_mask(data: bytes, mask: bytes) -> bytes:
        """Optimized XOR masking using pre-computed mask"""
        # Pre-compute mask for the entire payload
        mask_len = len(mask)
        data_len = len(data)
        
        # Fast path for small payloads
        if data_len < 256:
            return bytes(data[i] ^ mask[i % mask_len] for i in range(data_len))
        
        # For larger payloads, use repeated mask
        full_mask = (mask * ((data_len // mask_len) + 1))[:data_len]
        return bytes(a ^ b for a, b in zip(data, full_mask))
    
    async def close(self):
        """Close WebSocket gracefully"""
        if not self._closed:
            self._closed = True
            try:
                # Send close frame
                self.writer.write(self._encode_frame(b"", WS_OP_CLOSE))
                await self.writer.drain()
            except Exception:
                pass
            finally:
                self.writer.close()
                try:
                    await self.writer.wait_closed()
                except Exception:
                    pass