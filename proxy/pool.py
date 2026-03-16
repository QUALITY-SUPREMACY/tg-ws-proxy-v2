"""
Thread-safe WebSocket connection pool with parallel refill.
"""

import asyncio
import time
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

from .config import settings
from .websocket import RawWebSocket, WebSocketError

logger = logging.getLogger(__name__)


@dataclass
class PoolKey:
    """Pool key for DC + media flag"""
    dc_id: int
    is_media: bool = False


@dataclass
class PooledConnection:
    """Connection with metadata"""
    ws: RawWebSocket
    created_at: float = field(default_factory=time.monotonic)
    
    @property
    def age(self) -> float:
        return time.monotonic() - self.created_at


class ConnectionPool:
    """
    Thread-safe WebSocket connection pool with:
    - Parallel refill using asyncio.gather
    - Connection age tracking
    - Automatic cleanup of stale connections
    """
    
    def __init__(self):
        self._pools: Dict[PoolKey, List[PooledConnection]] = {}
        self._locks: Dict[PoolKey, asyncio.Lock] = {}
        self._refilling: set = set()
        self._dc_ips: Dict[int, str] = {}
        self._max_size = settings.ws_pool_size
        self._max_age = settings.ws_pool_max_age
        self._connect_timeout = settings.ws_connect_timeout
        
        # Parse DC IPs from config
        self._parse_dc_ips()
    
    def _parse_dc_ips(self):
        """Parse DC IP mappings from settings"""
        for mapping in settings.dc_ips:
            try:
                dc_id, ip = mapping.split(":", 1)
                self._dc_ips[int(dc_id)] = ip.strip()
            except ValueError:
                logger.warning(f"Invalid DC IP mapping: {mapping}")
    
    def _get_lock(self, key: PoolKey) -> asyncio.Lock:
        """Get or create lock for pool key"""
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]
    
    async def get(self, dc_id: int, is_media: bool = False) -> Optional[RawWebSocket]:
        """
        Get connection from pool.
        Returns None if no valid connection available.
        """
        key = PoolKey(dc_id, is_media)
        
        async with self._get_lock(key):
            pool = self._pools.get(key, [])
            
            # Clean stale connections and find valid one
            valid_conn = None
            remaining = []
            
            for conn in pool:
                if conn.ws.is_closed or conn.age > self._max_age:
                    # Close stale connection
                    try:
                        await conn.ws.close()
                    except Exception:
                        pass
                else:
                    if valid_conn is None:
                        valid_conn = conn
                    else:
                        remaining.append(conn)
            
            # Update pool
            if valid_conn:
                self._pools[key] = remaining
                return valid_conn.ws
            else:
                self._pools[key] = []
        
        # No valid connection, trigger refill
        await self._schedule_refill(key)
        return None
    
    async def put(self, ws: RawWebSocket, is_media: bool = False):
        """Return connection to pool"""
        if ws.is_closed:
            return
        
        key = PoolKey(ws.dc_id, is_media)
        
        async with self._get_lock(key):
            pool = self._pools.setdefault(key, [])
            
            # Don't exceed max size
            if len(pool) < self._max_size:
                pool.append(PooledConnection(ws))
            else:
                # Pool full, close connection
                try:
                    await ws.close()
                except Exception:
                    pass
    
    async def _schedule_refill(self, key: PoolKey):
        """Schedule pool refill if not already in progress"""
        if key in self._refilling:
            return
        
        self._refilling.add(key)
        try:
            await self._refill(key)
        finally:
            self._refilling.discard(key)
    
    async def _refill(self, key: PoolKey):
        """
        Refill pool with parallel connections.
        Uses asyncio.gather for parallel connection establishment.
        """
        target_ip = self._dc_ips.get(key.dc_id)
        if not target_ip:
            logger.error(f"No IP configured for DC{key.dc_id}")
            return
        
        async with self._get_lock(key):
            pool = self._pools.setdefault(key, [])
            needed = self._max_size - len(pool)
            
            if needed <= 0:
                return
        
        # Create connections in parallel
        async def try_connect() -> Optional[RawWebSocket]:
            try:
                return await RawWebSocket.connect(
                    target_ip,
                    key.dc_id,
                    key.is_media,
                    self._connect_timeout
                )
            except Exception as e:
                logger.debug(f"Connection failed: {e}")
                return None
        
        # Parallel connection attempts
        tasks = [try_connect() for _ in range(needed)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Add successful connections to pool
        async with self._get_lock(key):
            for result in results:
                if isinstance(result, RawWebSocket) and not result.is_closed:
                    pool.append(PooledConnection(result))
    
    async def cleanup(self):
        """Clean up all connections"""
        for key, pool in list(self._pools.items()):
            async with self._get_lock(key):
                for conn in pool:
                    try:
                        await conn.ws.close()
                    except Exception:
                        pass
                pool.clear()
        
        self._pools.clear()