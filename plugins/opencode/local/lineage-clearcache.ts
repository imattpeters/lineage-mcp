/**
 * lineage-mcp Plugin for OpenCode
 *
 * Automatically clears lineage-mcp caches on session start and when
 * OpenCode performs context compaction, ensuring the LLM receives
 * fresh instruction files and change detection on the next tool call.
 *
 * Setup:
 *   1. Copy this file to your project's .opencode/plugins/ directory
 *   2. Update CLEARCACHE_SCRIPT below to your lineage-mcp install path
 *   3. Add {"dependencies":{"@opencode-ai/plugin":"latest"}} to .opencode/package.json
 *   4. Restart OpenCode — the plugin auto-loads at startup
 */

import type { Plugin } from "@opencode-ai/plugin";
import { spawn } from "child_process";

const CLIENT_NAME = "opencode";

// ⚠️ UPDATE THIS PATH to your lineage-mcp installation
const CLEARCACHE_SCRIPT = "/path/to/lineage-mcp/hooks/clearcache.py";

/**
 * Spawn hooks/clearcache.py and pipe JSON to stdin.
 * Returns the stderr output on success.
 */
function sendClearByFilter(directory: string, hookEvent: string = "PreCompact"): Promise<string> {
  return new Promise((resolve_val, reject) => {
    const proc = spawn("python", [CLEARCACHE_SCRIPT, CLIENT_NAME], {
      stdio: ["pipe", "pipe", "pipe"],
    });

    proc.stdin.write(JSON.stringify({ cwd: directory, hook_event_name: hookEvent }));
    proc.stdin.end();

    let stderr = "";
    proc.stderr.on("data", (chunk: Buffer) => {
      stderr += chunk.toString();
    });
    proc.on("close", (code: number | null) => {
      if (code === 0) resolve_val(stderr.trim());
      else reject(new Error(`clearcache.py exited with code ${code}`));
    });
    proc.on("error", reject);
  });
}

export const LineageMcpPlugin: Plugin = async (ctx) => {
  return {
    /**
     * Fires when a new session is created.
     * Clears stale caches from previous sessions.
     */
    "session.created": async (_input, _output) => {
      try {
        const result = await sendClearByFilter(ctx.directory, "SessionStart");

        if (result.includes("Cleared")) {
          await ctx.client.app.log({
            body: {
              service: "lineage-mcp",
              level: "info",
              message: `lineage-mcp: ${result} (session start)`,
            },
          });
        }
      } catch {
        // Tray not running or Python not available — silent no-op
      }
    },

    /**
     * Fires before context compaction occurs.
     * Clears lineage-mcp caches via the tray's named pipe.
     */
    "experimental.session.compacting": async (_input, _output) => {
      try {
        const result = await sendClearByFilter(ctx.directory, "PreCompact");

        if (result.includes("Cleared")) {
          await ctx.client.app.log({
            body: {
              service: "lineage-mcp",
              level: "info",
              message: `lineage-mcp: ${result}`,
            },
          });
        }
      } catch {
        // Tray not running or Python not available — silent no-op
      }
    },

    /**
     * Fires after context compaction completes.
     * Secondary hook — clears caches if pre-compaction hook missed.
     */
    "session.compacted": async (_input, _output) => {
      try {
        await sendClearByFilter(ctx.directory, "PreCompact");
      } catch {
        // Tray not running or Python not available — silent no-op
      }
    },
  };
};
