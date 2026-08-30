"""Configuracao da aplicacao. Unico ponto do sistema que le variavel de ambiente."""
import os
from dataclasses import dataclass, field
from functools import lru_cache


@dataclass(frozen=True)
class LLMSettings:
    """O hub fala o protocolo OpenAI-compativel. Trocar de provedor e trocar
    base_url + model, sem tocar em uma linha de codigo (DIP)."""
    base_url: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    api_key: str = os.getenv("LLM_API_KEY", "")
    model: str = os.getenv("LLM_MODEL", "gpt-5")
    timeout: float = float(os.getenv("LLM_TIMEOUT", "12"))
    max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "400"))

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)


@dataclass(frozen=True)
class WhatsAppSettings:
    """Integração com a WhatsApp Business Cloud API (Meta Graph API).

    Canal principal do MVP. Enquanto `enabled` for falso o hub opera apenas com
    o simulador — útil em desenvolvimento, onde não há webhook público.
    """
    enabled: bool = os.getenv("WHATSAPP_ENABLED", "false").lower() == "true"
    api_version: str = os.getenv("WHATSAPP_API_VERSION", "v21.0")
    phone_number_id: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    business_account_id: str = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", "")
    access_token: str = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    verify_token: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    app_secret: str = os.getenv("WHATSAPP_APP_SECRET", "")
    default_recipient: str = os.getenv("WHATSAPP_DEFAULT_RECIPIENT", "")
    timeout: float = float(os.getenv("WHATSAPP_TIMEOUT", "10"))

    @property
    def graph_url(self) -> str:
        return f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"

    @property
    def configured(self) -> bool:
        """Credenciais presentes. Distinto de `enabled`: dá para configurar sem ligar."""
        return bool(self.phone_number_id and self.access_token)

    @property
    def can_send(self) -> bool:
        return self.enabled and self.configured

    @property
    def verifies_signature(self) -> bool:
        return bool(self.app_secret)

    def missing(self) -> list[str]:
        """Quais variáveis faltam — a interface mostra isto na tela de status."""
        required = {
            "WHATSAPP_PHONE_NUMBER_ID": self.phone_number_id,
            "WHATSAPP_ACCESS_TOKEN": self.access_token,
            "WHATSAPP_VERIFY_TOKEN": self.verify_token,
        }
        return [name for name, value in required.items() if not value]


@dataclass(frozen=True)
class Settings:
    app_name: str = "Claro Conversation Hub API"
    version: str = "1.0.0"
    environment: str = os.getenv("ENVIRONMENT", "development")
    public_url: str = os.getenv("PUBLIC_URL", "http://localhost:8000")

    redis_url: str = os.getenv("REDIS_URL", "")
    mongo_url: str = os.getenv("MONGO_URL", "")
    mongo_db: str = os.getenv("MONGO_DB", "claro_hub")

    session_ttl_seconds: int = int(os.getenv("SESSION_TTL_SECONDS", "1800"))
    handover_confidence_threshold: float = float(
        os.getenv("HANDOVER_CONFIDENCE_THRESHOLD", "0.55"))

    llm: LLMSettings = field(default_factory=LLMSettings)
    whatsapp: WhatsAppSettings = field(default_factory=WhatsAppSettings)

    cors_origins: tuple[str, ...] = tuple(
        o.strip() for o in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://localhost:4173,http://localhost:3000",
        ).split(",") if o.strip()
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
