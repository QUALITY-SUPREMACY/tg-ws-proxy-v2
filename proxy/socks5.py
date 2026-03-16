"""
SOCKS5 protocol implementation.
"""

import asyncio
import struct
from typing import Optional, Tuple
from enum import IntEnum
import logging

from .config import settings

logger = logging.getLogger(__name__)


class Socks5AuthMethod(IntEnum):
    NO_AUTH = 0x00
    USERNAME_PASSWORD = 0x02
    NO_ACCEPTABLE = 0xFF


class Socks5Command(IntEnum):
    CONNECT = 0x01
    BIND = 0x02
    UDP_ASSOCIATE = 0x03


class Socks5AddressType(IntEnum):
    IPV4 = 0x01
    DOMAIN = 0x03
    IPV6 = 0x04


class Socks5Error(Exception):
    """SOCKS5 protocol error"""
    pass


class Socks5Server:
    """SOCKS5 server implementation with optional authentication"""
    
    def __init__(self):
        self.auth_enabled = settings.auth_enabled
        self.username = settings.auth_username
        self.password = settings.auth_password
    
    async def handshake(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> bool:
        """
        Perform SOCKS5 handshake.
        Returns True if successful, False otherwise.
        """
        # Read greeting
        data = await reader.readexactly(2)
        version, nmethods = struct.unpack("!BB", data)
        
        if version != 0x05:
            raise Socks5Error(f"Unsupported SOCKS version: {version}")
        
        # Read methods
        methods = await reader.readexactly(nmethods)
        
        # Select auth method
        if self.auth_enabled and Socks5AuthMethod.USERNAME_PASSWORD in methods:
            selected = Socks5AuthMethod.USERNAME_PASSWORD
        elif not self.auth_enabled and Socks5AuthMethod.NO_AUTH in methods:
            selected = Socks5AuthMethod.NO_AUTH
        else:
            selected = Socks5AuthMethod.NO_ACCEPTABLE
        
        # Send method selection
        writer.write(struct.pack("!BB", 0x05, selected))
        await writer.drain()
        
        if selected == Socks5AuthMethod.NO_ACCEPTABLE:
            raise Socks5Error("No acceptable authentication method")
        
        # Handle authentication if required
        if selected == Socks5AuthMethod.USERNAME_PASSWORD:
            return await self._authenticate(reader, writer)
        
        return True
    
    async def _authenticate(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> bool:
        """Handle username/password authentication"""
        # Read auth request
        data = await reader.readexactly(2)
        version, ulen = struct.unpack("!BB", data)
        
        if version != 0x01:
            raise Socks5Error(f"Unsupported auth version: {version}")
        
        # Read username
        username = await reader.readexactly(ulen)
        
        # Read password length and password
        data = await reader.readexactly(1)
        plen = data[0]
        password = await reader.readexactly(plen)
        
        # Validate credentials
        valid = (
            username.decode('utf-8', errors='replace') == self.username and
            password.decode('utf-8', errors='replace') == self.password
        )
        
        # Send response
        status = 0x00 if valid else 0x01
        writer.write(struct.pack("!BB", 0x01, status))
        await writer.drain()
        
        return valid
    
    async def read_request(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> Tuple[Socks5Command, str, int]:
        """
        Read SOCKS5 request.
        Returns: (command, target_host, target_port)
        """
        # Read request header
        data = await reader.readexactly(4)
        version, cmd, reserved, atyp = struct.unpack("!BBBB", data)
        
        if version != 0x05:
            raise Socks5Error(f"Invalid version in request: {version}")
        
        if reserved != 0x00:
            raise Socks5Error(f"Invalid reserved byte: {reserved}")
        
        cmd = Socks5Command(cmd)
        atyp = Socks5AddressType(atyp)
        
        # Read address
        if atyp == Socks5AddressType.IPV4:
            data = await reader.readexactly(4)
            host = '.'.join(str(b) for b in data)
        
        elif atyp == Socks5AddressType.DOMAIN:
            data = await reader.readexactly(1)
            dlen = data[0]
            if dlen > 255:
                raise Socks5Error(f"Domain name too long: {dlen}")
            host = (await reader.readexactly(dlen)).decode('utf-8', errors='replace')
        
        elif atyp == Socks5AddressType.IPV6:
            # IPv6 not supported
            await self._send_reply(writer, 0x08)  # Address type not supported
            raise Socks5Error("IPv6 not supported")
        
        else:
            await self._send_reply(writer, 0x08)
            raise Socks5Error(f"Unknown address type: {atyp}")
        
        # Read port
        data = await reader.readexactly(2)
        port = struct.unpack("!H", data)[0]
        
        # Check command
        if cmd != Socks5Command.CONNECT:
            await self._send_reply(writer, 0x07)  # Command not supported
            raise Socks5Error(f"Command not supported: {cmd}")
        
        return cmd, host, port
    
    async def send_success_reply(self, writer: asyncio.StreamWriter, bind_addr: str = "0.0.0.0", bind_port: int = 0):
        """Send success reply to client"""
        await self._send_reply(writer, 0x00, bind_addr, bind_port)
    
    async def send_error_reply(self, writer: asyncio.StreamWriter, code: int = 0x01):
        """Send error reply to client"""
        await self._send_reply(writer, code)
    
    async def _send_reply(self, writer: asyncio.StreamWriter, code: int, bind_addr: str = "0.0.0.0", bind_port: int = 0):
        """Send SOCKS5 reply"""
        addr_bytes = bytes(int(b) for b in bind_addr.split('.'))
        writer.write(struct.pack("!BBBB", 0x05, code, 0x00, 0x01) + addr_bytes + struct.pack("!H", bind_port))
        await writer.drain()