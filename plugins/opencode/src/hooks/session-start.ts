/**
 * SessionStart hook for OpenCode.
 *
 * Fires when a new session is created, triggering cache clearing
 * in lineage-mcp via the tray so stale data from previous sessions
 * doesn't pollute the new session.
 */

import type { PluginInput } from "@opencode-ai/plugin";
import { sendClearByFilter } from "../tray-client";

const CLIENT_NAME = "opencode";

/**
 * Handle the session.created event.
 *
 * Clears lineage-mcp caches from any previous session so the LLM
 * starts fresh with accurate file state and instruction files.
 */
export async function handleSessionCreated(ctx: PluginInput): Promise<void> {
  try {
    const sessionsCleared = await sendClearByFilter(ctx.directory, CLIENT_NAME);

    if (sessionsCleared > 0) {
      ctx.client.app.log({
        body: {
          service: "lineage-mcp",
          level: "info",
          message: `Cleared lineage-mcp cache for ${sessionsCleared} session(s) on session start`,
        },
      });
    }
  } catch {
    // Silently ignore errors - lineage-mcp is optional
    ctx.client.app.log({
      body: {
        service: "lineage-mcp",
        level: "debug",
        message: "Failed to clear lineage-mcp cache on session start (tray may not be running)",
      },
    });
  }
}
