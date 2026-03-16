"""
MTProto protocol utilities.
"""

import struct
from typing import Optional, Tuple
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from .telegram_const import (
    MTPROTO_MAGIC,
    MTPROTO_MAGIC_OFFSET,
    MTPROTO_DC_OFFSET,
    is_telegram_ip
)


def extract_dc_from_init(data: bytes) -> Optional[Tuple[int, bool]]:
    """
    Extract DC ID and media flag from MTProto obfuscation init packet.
    Returns (dc_id, is_media) or None if not valid.
    """
    if len(data) < 64:
        return None
    
    # Check magic bytes
    magic = data[MTPROTO_MAGIC_OFFSET:MTPROTO_MAGIC_OFFSET + 4]
    if magic != MTPROTO_MAGIC:
        return None
    
    # Extract DC ID from bytes 60-64
    dc_bytes = data[MTPROTO_DC_OFFSET:MTPROTO_DC_OFFSET + 4]
    dc_val = struct.unpack("!I", dc_bytes)[0]
    
    # DC ID is lower 16 bits
    dc_id = dc_val & 0xFFFF
    
    # Media flag is bit 16
    is_media = bool(dc_val & 0x10000)
    
    # Validate DC ID
    if dc_id < 1 or dc_id > 5:
        return None
    
    return (dc_id, is_media)


def patch_dc_in_init(data: bytes, new_dc: int) -> bytes:
    """
    Patch DC ID in MTProto init packet.
    Used for Android clients with useSecret=0.
    """
    if len(data) < 64:
        return data
    
    # Read current value
    dc_bytes = data[MTPROTO_DC_OFFSET:MTPROTO_DC_OFFSET + 4]
    dc_val = struct.unpack("!I", dc_bytes)[0]
    
    # Keep flags, replace DC
    new_val = (dc_val & ~0xFFFF) | (new_dc & 0xFFFF)
    new_bytes = struct.pack("!I", new_val)
    
    # Replace in data
    return data[:MTPROTO_DC_OFFSET] + new_bytes + data[MTPROTO_DC_OFFSET + 4:]


class MTProtoSplitter:
    """
    Split MTProto stream into individual messages.
    """
    
    def __init__(self):
        self._buffer = b""
    
    def feed(self, data: bytes) -> list:
        """
        Feed data and return complete messages.
        MTProto uses 4-byte little-endian length prefix.
        """
        self._buffer += data
        messages = []
        
        while len(self._buffer) >= 4:
            # Read length (little-endian)
            length = struct.unpack("<I", self._buffer[:4])[0]
            
            # Check if we have complete message
            if len(self._buffer) < 4 + length:
                break
            
            # Extract message
            message = self._buffer[4:4 + length]
            messages.append(message)
            
            # Remove from buffer
            self._buffer = self._buffer[4 + length:]
        
        return messages
    
    def pack(self, message: bytes) -> bytes:
        """Pack message with length prefix"""
        return struct.pack("<I", len(message)) + message


def is_http_transport(data: bytes) -> bool:
    """Check if data looks like HTTP (not MTProto)"""
    if len(data) < 8:
        return False
    
    http_methods = (b"GET ", b"POST ", b"HEAD ", b"PUT ", b"DELETE")
    return any(data.startswith(method) for method in http_methods)