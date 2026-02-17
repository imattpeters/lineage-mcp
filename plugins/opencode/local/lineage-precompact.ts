/**
 * lineage-mcp PreCompact Plugin for OpenCode
 *
 * Automatically clears lineage-mcp caches when OpenCode performs
 * context compaction, ensuring the LLM receives fresh instruction
 * files and change detection on the next tool call.
 *
 * Setup:
 *   1. Copy this file to your project's .opencode/plugins/ directory
 *   2. Update PRECOMPACT_SCRIPT below to your lineage-mcp install path
 *   3. Add {"dependencies":{"@opencode-ai/plugin":"latest"}} to .opencode/package.json
 *   4. Restart OpenCode — the plugin auto-loads at startup
 */

import type { Plugin } from "@opencode-ai/plugin";
import { spawn } from "child_process";

const CLIENT_NAME = "opencode";

// ⚠️ UPDATE THIS PATH to your lineage-mcp installation
const PRECOMPACT_SCRIPT = "/path/to/lineage-mcp/hooks/precompact.py";

/**
 * Spawn hooks/precompact.py and pipe JSON to stdin.
 * Returns the stderr output on success.
 */
function sendClearByFilter(directory: string): Promise<string> {
  return new Promise((resolve_val, reject) => {
    const proc = spawn("python", [PRECOMPACT_SCRIPT, CLIENT_NAME], {
      stdio: ["pipe", "pipe", "pipe"],
    });

    proc.stdin.write(JSON.stringify({ cwd: directory }));
    proc.stdin.end();

    let stderr = "";
    proc.stderr.on("data", (chunk: Buffer) => {
      stderr += chunk.toString();
    });
    proc.on("close", (code: number | null) => {
      if (code === 0) resolve_val(stderr.trim());
      else reject(new Error(`precompact.py exited with code ${code}`));
    });
    proc.on("error", reject);
  });
}

export const LineageMcpPlugin: Plugin = async (ctx) => {
  return {
    /**
     * Fires before context compaction occurs.
     * Clears lineage-mcp caches via the tray's named pipe.
     */
    "experimental.session.compacting": async (_input, _output) => {
      try {
        const result = await sendClearByFilter(ctx.directory);

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
        await sendClearByFilter(ctx.directory);
      } catch {
        // Tray not running or Python not available — silent no-op
      }
    },
  };
};
