"""Casos de uso do Design Studio (RF006).

Salvar aqui muda o comportamento de todos os canais na proxima mensagem --
nao ha deploy, nao ha reinicio. E o que torna a persona um parametro do sistema
em vez de codigo espalhado pelas integracoes.
"""
from __future__ import annotations

from ...domain.ports import AuditLog, StudioConfigRepository
from ...domain.studio import StudioConfig


class GetStudioConfigUseCase:
    def __init__(self, repository: StudioConfigRepository) -> None:
        self._repository = repository

    async def execute(self) -> StudioConfig:
        return await self._repository.get()


class UpdateStudioConfigUseCase:
    def __init__(self, repository: StudioConfigRepository, audit: AuditLog) -> None:
        self._repository = repository
        self._audit = audit

    async def execute(self, config: StudioConfig) -> StudioConfig:
        saved = await self._repository.save(config)
        await self._audit.record("studio.config.updated", None, {
            "persona": saved.persona.name,
            "channels": [c.id for c in saved.channels],
            "intents": len(saved.intents),
        })
        return saved


class UpdateChannelConfigUseCase:
    """Atualiza a configuracao de um unico canal, preservando os demais."""

    def __init__(self, repository: StudioConfigRepository, audit: AuditLog) -> None:
        self._repository = repository
        self._audit = audit

    async def execute(self, channel_id: str, patch: dict) -> StudioConfig | None:
        config = await self._repository.get()
        target = config.channel(channel_id)
        if target is None:
            return None

        updated = target.model_copy(update=patch)
        config.channels = [updated if c.id == channel_id else c for c in config.channels]

        saved = await self._repository.save(config)
        await self._audit.record("studio.channel.updated", None,
                                 {"channel": channel_id, "fields": sorted(patch)})
        return saved
