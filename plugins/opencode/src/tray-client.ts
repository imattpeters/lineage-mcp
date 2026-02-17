/**
 * Client for communicating with lineage-mcp-tray via Named Pipe.
 *
 * Connects to the tray's multiprocessing.connection Listener and
 * sends clear_by_filter messages when compaction occurs.
 *
 * Uses the Python hook script (hooks/precompact.py) via child_process
 * to handle the multiprocessing.connection protocol from Node.js.
 */

import { spawn } from "child_process";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export interface ClearByFilterMessage {
  type: "clear_by_filter";
  base_dir: string;
  client_name: string;
}

export interface TrayResponse {
  sessions_cleared: number;
}

/**
 * Send a clear_by_filter message to the tray.
 *
 * Uses the Python hook script via child_process to handle the
 * multiprocessing.connection protocol from Node.js.
 *
 * @param baseDir - The project base directory
 * @param clientName - The client identifier (e.g., "opencode")
 * @returns Promise resolving to number of sessions cleared
 */
export async function sendClearByFilter(
  baseDir: string,
  clientName: string
): Promise<number> {
  return new Promise((resolve_val, reject) => {
    // Path to the Python hook script
    // From dist/tray-client.js → plugins/opencode/ → plugins/ → lineage-mcp repo root
    const scriptPath = resolve(__dirname, "../../../hooks/precompact.py");

    // Spawn Python process
    const python = spawn("python", [scriptPath, clientName], {
      stdio: ["pipe", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";

    python.stdout.on("data", (data) => {
      stdout += data.toString();
    });

    python.stderr.on("data", (data) => {
      stderr += data.toString();
    });

    python.on("close", (code: number | null) => {
      if (code === 0) {
        // Parse "Cleared N session(s)" from stderr
        const match = stderr.match(/Cleared (\d+) session/);
        resolve_val(match ? parseInt(match[1], 10) : 0);
      } else {
        // Tray not running or other error - silent no-op
        resolve_val(0);
      }
    });

    python.on("error", () => {
      // Python not available - silent no-op
      resolve_val(0);
    });

    // Send hook input JSON to stdin
    const hookInput = JSON.stringify({
      cwd: baseDir,
      hook_event_name: "PreCompact",
      client: clientName,
    });

    python.stdin.write(hookInput);
    python.stdin.end();
  });
}
