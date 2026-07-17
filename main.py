"""DeckySense backend entrypoint.

Decky Loader instantiates the ``Plugin`` class below once per plugin
lifecycle and invokes the underscore-prefixed hooks at the right
moments. Any other ``async def`` method on this class becomes an RPC
callable from the TypeScript frontend via ``@decky/api``'s
``callable("method_name")``.
"""

from __future__ import annotations

import asyncio
from typing import Any

import decky

from deckysense.updater import self_updater


class Plugin:
    """Lifecycle handler for the DeckySense backend."""

    loop: asyncio.AbstractEventLoop

    async def _main(self) -> None:
        self.loop = asyncio.get_event_loop()
        decky.logger.info(
            "DeckySense backend started (v%s)", self_updater.CURRENT_VERSION
        )

    async def _unload(self) -> None:
        decky.logger.info("DeckySense backend stopping")

    async def _uninstall(self) -> None:
        decky.logger.info("DeckySense uninstalled")

    async def _migration(self) -> None:
        decky.logger.info("DeckySense migration check (no-op)")

    # --- RPC: updater ----------------------------------------------------

    async def get_current_version(self) -> str:
        return self_updater.CURRENT_VERSION

    async def check_for_update(self, force: bool = False) -> dict[str, Any]:
        return await self.loop.run_in_executor(None, self_updater.check, force)

    async def install_update(self) -> dict[str, Any]:
        return await self.loop.run_in_executor(None, self_updater.install)

    async def restart_loader(self) -> dict[str, Any]:
        return await self.loop.run_in_executor(None, self_updater.restart_loader)
