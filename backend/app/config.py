import json
from typing import List, Literal, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central application configuration loaded from environment variables.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    PROJECT_NAME: str = "Delegation Chain Governor"
    VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["development", "production", "test"] = "development"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # MongoDB Configuration
    MONGODB_URI: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection string (local or MongoDB Atlas URI)"
    )
    MONGODB_DB_NAME: str = "delegation_governor"
    MONGODB_CONNECT_TIMEOUT_MS: int = 5000
    MONGODB_SERVER_SELECTION_TIMEOUT_MS: int = 5000

    # CORS Configuration
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000"
    ]

    # Cryptography: Ed25519 Private Key Hex (Optional: auto-generated if omitted)
    ED25519_PRIVATE_KEY_HEX: Optional[str] = None
    ED25519_PUBLIC_KEY_HEX: Optional[str] = None

    # Google Gemini LLM Configuration
    GEMINI_API_KEY: Optional[str] = Field(
        default=None,
        description="Google Gemini API Key (loaded securely from environment, never exposed)"
    )
    GEMINI_MODEL: str = Field(
        default="gemini-3.6-flash",
        description="Target Gemini model identifier (e.g. gemini-3.6-flash)"
    )
    LLM_TIMEOUT_SECONDS: float = Field(
        default=45.0,
        ge=1.0,
        le=120.0,
        description="Timeout for LLM generation requests"
    )
    LLM_MAX_RETRIES: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Max safe retries for transient LLM generation failures"
    )

    # Delegation Policy Constants
    MAX_DELEGATION_DEPTH: int = Field(default=4, ge=1, le=10)
    DEFAULT_TOKEN_TTL_SECONDS: int = Field(default=300, ge=1, le=3600)
    HTTP_TIMEOUT_SECONDS: float = Field(default=10.0, ge=1.0, le=60.0)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, list):
            return v
        raise ValueError("Invalid format for CORS_ORIGINS")

    @field_validator("MONGODB_URI")
    @classmethod
    def validate_mongodb_uri(cls, v: str) -> str:
        if not v or not (v.startswith("mongodb://") or v.startswith("mongodb+srv://")):
            raise ValueError("MONGODB_URI must start with 'mongodb://' or 'mongodb+srv://'")
        return v


# Global singleton settings instance
settings = Settings()
