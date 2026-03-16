"""
Main proxy server with graceful shutdown.
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

from .config import settings
from .socks5 import Socks5Server, Socks5Error
from .rate_limiter import RateLimiter
from .pool import ConnectionPool
from .bridge import Bridge
from .mtproto import extract_dc_from_init, patch_dc_in_init, is_http_transport
from .telegram_const import is_telegram_ip

logger = logging.getLogger(__name__)


class ProxyServer:
    """SOCKS5 proxy server with WebSocket bridge"""
    
    def __init__(self):
        self.socks5 = Socks5Server()
        self.rate_limiter = RateLimiter()
        self.pool = ConnectionPool()
        self.bridge = Bridge(self.pool)
        self.server: Optional[asyncio.Server] = None
        self._shutdown_event = asyncio.Event()
        self._active_connections: set = set()
        self._lock = asyncio.Lock()
    
    async def start(self):
        """Start the proxy server"""
        # Setup logging
        self._setup_logging()
        
        # Setup signal handlers
        for sig in (signal.SIGTERM, signal.SIGINT):
            asyncio.get_event_loop().add_signal_handler(
                sig, lambda: asyncio.create_task(self.shutdown())
            )
        
        # Start server
        self.server = await asyncio.start_server(
            self._handle_client,
            settings.proxy_host,
            settings.proxy_port
        )
        
        addr = self.server.sockets[0].getsockname()
        logger.info(f"Proxy server started on {addr[0]}:{addr[1]}")
        logger.info(f"WebSocket pool size: {settings.ws_pool_size}")
        logger.info(f"Rate limit: {settings.rate_limit_connections}/min")
        
        # Run until shutdown
        await self._shutdown_event.wait()
    
    def _setup_logging(self):
        """Configure logging"""
        level = getattr(logging, settings.log_level.upper())
        
        if settings.log_json:
            # JSON logging
            import structlog
            structlog.configure(
                processors=[
                    structlog.stdlib.filter_by_level,
                    structlog.stdlib.add_logger_name,
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.PositionalArgumentsFormatter(),
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.StackInfoRenderer(),
                    structlog.processors.format_exc_info,
                    structlog.processors.UnicodeDecoder(),
                    structlog.processors.JSONRenderer()
                ],
                context_class=dict,
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
                cache_logger_on_first_use=True,
            )
        else:
            # Plain text logging
            logging.basicConfig(
                level=level,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                stream=sys.stdout
            )
    
    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ):
        """Handle incoming client connection"""
        client_addr = writer.get_extra_info('peername')
        client_ip = client_addr[0] if client_addr else "unknown"
        
        # Track connection
        async with self._lock:
            self._active_connections.add(asyncio.current_task())
        
        try:
            # Rate limiting
            if not await self.rate_limiter.is_allowed(client_ip):
                logger.warning(f"Rate limit exceeded for {client_ip}")
                writer.close()
                return
            
            # SOCKS5 handshake
            try:
                auth_ok = await self.socks5.handshake(reader, writer)
                if not auth_ok:
                    logger.warning(f"Authentication failed for {client_ip}")
                    return
            except Socks5Error as e:
                logger.debug(f"SOCKS5 handshake error: {e}")
                return
            
            # Read request
            try:
                _, target_host, target_port = await self.socks5.read_request(reader, writer)
            except Socks5Error as e:
                logger.debug(f"SOCKS5 request error: {e}")
                return
            
            logger.debug(f"Connection to {target_host}:{target_port} from {client_ip}")
            
            # Check if target is Telegram
            if not is_telegram_ip(target_host):
                # Not Telegram, do direct connection
                await self.socks5.send_error_reply(writer, 0x05)  # Connection refused
                return
            
            # Send success reply
            await self.socks5.send_success_reply(writer)
            
            # Read init packet (MTProto obfuscation)
            init_data = await reader.read(64)
            if len(init_data) < 64:
                logger.debug("Incomplete init packet")
                return
            
            # Check if HTTP transport (not MTProto)
            if is_http_transport(init_data):
                # Direct TCP for HTTP
                await self.bridge.bridge_tcp(reader, writer, target_host, target_port)
                return
            
            # Extract DC from init packet
            dc_info = extract_dc_from_init(init_data)
            
            if dc_info:
                dc_id, is_media = dc_info
                logger.debug(f"Detected DC{dc_id} (media={is_media})")
                
                # Handle Telegram connection
                await self.bridge.handle_telegram_connection(
                    reader, writer, dc_id, is_media, init_data
                )
            else:
                # Fallback to direct TCP
                logger.debug(f"Could not extract DC, using direct TCP")
                await self.bridge.bridge_tcp(reader, writer, target_host, target_port)
        
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Error handling client {client_ip}: {e}")
        finally:
            # Cleanup
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            
            async with self._lock:
                self._active_connections.discard(asyncio.current_task())
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down proxy server...")
        
        # Stop accepting new connections
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        # Cancel active connections
        async with self._lock:
            tasks = list(self._active_connections)
        
        if tasks:
            logger.info(f"Waiting for {len(tasks)} active connections...")
            for task in tasks:
                task.cancel()
            
            # Wait with timeout
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Cleanup pool
        await self.pool.cleanup()
        
        logger.info("Proxy server stopped")
        self._shutdown_event.set()


def main():
    """Entry point"""
    server = ProxyServer()
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()