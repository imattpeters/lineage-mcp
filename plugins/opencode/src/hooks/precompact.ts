/**
 * PreCompact hook for OpenCode.
 *
 * Fires when context compaction is about to occur, triggering
 * cache clearing in lineage-mcp via the tray.
 */

import type { PluginInput } from "@opencode-ai/plugin";
import { sendClearByFilter } from "../tray-client";

const CLIENT_NAME = "opencode";

/**
 * Handle the experimental.session.compacting event.
 *
 * This fires BEFORE compaction occurs, giving us a chance to
 * clear lineage-mcp caches while the full context is still available.
 */
export async function handleCompacting(ctx: PluginInput): Promise<void> {
  try {
    const sessionsCleared = await sendClearByFilter(ctx.directory, CLIENT_NAME);

    if (sessionsCleared > 0) {
      ctx.client.app.log({
        body: {
          service: "lineage-mcp",
          level: "info",
          message: `Cleared lineage-mcp cache for ${sessionsCleared} session(s) before compaction`,
        },
      });
    }
  } catch {
    // Silently ignore errors - lineage-mcp is optional
    ctx.client.app.log({
      body: {
        service: "lineage-mcp",
        level: "debug",
        message: "Failed to clear lineage-mcp cache (tray may not be running)",
      },
    });
  }
}
