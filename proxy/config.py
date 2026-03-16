from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional


class Settings(BaseSettings):
    """CS3NEWS GIGAVPN Configuration"""
    
    # Server settings
    proxy_host: str = Field(default="127.0.0.1", description="SOCKS5 listen host")
    proxy_port: int = Field(default=1080, description="SOCKS5 listen port")
    
    # WebSocket pool settings
    ws_pool_size: int = Field(default=8, ge=1, le=32, description="Connection pool size")
    ws_pool_max_age: float = Field(default=120.0, ge=30.0, description="Max connection age (seconds)")
    ws_connect_timeout: float = Field(default=5.0, ge=1.0, description="Connect timeout")
    
    # Rate limiting
    rate_limit_connections: int = Field(default=100, ge=10, description="Max connections per minute per IP")
    rate_limit_burst: int = Field(default=10, ge=1, description="Burst size")
    
    # Security
    auth_enabled: bool = Field(default=False, description="Enable SOCKS5 authentication")
    auth_username: Optional[str] = Field(default=None, description="SOCKS5 username")
    auth_password: Optional[str] = Field(default=None, description="SOCKS5 password")
    
    # Target endpoints (format: "id:ip_address")
    target_endpoints: List[str] = Field(
        default=["2:149.154.167.220", "4:149.154.167.220"],
        description="Target endpoint mappings"
    )
    
    # Logging
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR)$")
    log_json: bool = Field(default=False, description="Use JSON logging")
    
    # Performance
    recv_buf_size: int = Field(default=65536, ge=4096, le=262144)
    send_buf_size: int = Field(default=65536, ge=4096, le=262144)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()