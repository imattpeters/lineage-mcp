/**
 * lineage-mcp OpenCode Plugin
 *
 * Automatically clears lineage-mcp caches when OpenCode performs
 * context compaction, ensuring the LLM receives fresh instruction
 * files and change detection on the next tool call.
 */

import type { Plugin } from "@opencode-ai/plugin";
import { handleCompacting } from "./hooks/precompact";

/**
 * Main plugin export.
 *
 * Registers hooks for session lifecycle events.
 */
export const LineageMcpPlugin: Plugin = async (ctx) => {
  return {
    /**
     * Fires before context compaction occurs.
     *
     * This is the OpenCode equivalent of Claude Code's PreCompact hook.
     * We use this to proactively clear lineage-mcp caches.
     */
    "experimental.session.compacting": async (
      _input: unknown,
      _output: unknown
    ) => {
      await handleCompacting(ctx);
    },

    /**
     * Fires after context compaction completes.
     *
     * Secondary opportunity to clear caches if the pre-compaction
     * hook failed or if we want to track compaction events.
     */
    "session.compacted": async (_input: unknown, _output: unknown) => {
      // Optional: Could re-clear here as a safety net
      // For now, we rely on the pre-compaction hook
    },
  };
};

export default LineageMcpPlugin;
