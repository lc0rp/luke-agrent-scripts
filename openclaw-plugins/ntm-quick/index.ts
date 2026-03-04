import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { readFile, writeFile } from "node:fs/promises";
import { homedir } from "node:os";
import { join } from "node:path";
import {
  resolveAsyncReplyOrigin,
  resolveAsyncReplyTarget,
  sendAsyncReply,
  type CommandInvocationContext,
} from "./async-reply";

const DEFAULT_TIMEOUT_MS = 90_000;
const DEFAULT_POLL_INTERVAL_MS = 1_000;
const DEFAULT_ROBOT_TAIL_LINES = 120;
const DEFAULT_NCAT_LINES = 50;
const DEFAULT_PTY_ROWS = 40;
const DEFAULT_PTY_COLS = 120;
const NTM_QUICK_STATE_PATH =
  process.env.CLAWD_NTM_QUICK_STATE_FILE?.trim() ||
  join(homedir(), ".clawd-ntm-quick.json");

const NO_OUTPUT_PROMPT_RE = /^\s*(>|❯|input:?|codex\s*>?)\s*$/i;
const NO_OUTPUT_CHEVRON_RE = /^\s*›\s*/;
const NO_OUTPUT_CONTEXT_HINT_RE = /for shortcuts.*context left/i;
const NO_OUTPUT_RULE_RE = /^[-─]{8,}$/;
const NO_OUTPUT_ACTIVITY_RE = /(?:^|[•◦]\s*)working\s*\(.*esc to interrupt\)/i;

type NtmResult = {
  stdout?: string;
  stderr?: string;
  code?: number;
};

type NtmQuickState = {
  project?: string;
};

type RobotPollResult = {
  response?: string;
  error?: string;
  timedOut?: boolean;
};

function normalizeOutput(text: string): string {
  return text.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
}

function splitFirstToken(input: string): { token: string; rest: string } {
  const trimmed = input.trim();
  if (!trimmed) return { token: "", rest: "" };

  const firstWhitespace = trimmed.search(/\s/);
  if (firstWhitespace === -1) return { token: trimmed, rest: "" };

  return {
    token: trimmed.slice(0, firstWhitespace),
    rest: trimmed.slice(firstWhitespace).trim(),
  };
}

function getTimeoutMs(): number {
  const parsed = Number.parseInt(process.env.NTM_QUICK_TIMEOUT_MS ?? "", 10);
  if (!Number.isFinite(parsed) || parsed <= 0) return DEFAULT_TIMEOUT_MS;
  return parsed;
}

function getPollIntervalMs(): number {
  const parsed = Number.parseInt(process.env.NTM_QUICK_POLL_INTERVAL_MS ?? "", 10);
  if (!Number.isFinite(parsed) || parsed <= 0) return DEFAULT_POLL_INTERVAL_MS;
  return parsed;
}

function getRobotTailLines(): number {
  const parsed = Number.parseInt(process.env.NTM_QUICK_ROBOT_TAIL_LINES ?? "", 10);
  if (!Number.isFinite(parsed) || parsed <= 0) return DEFAULT_ROBOT_TAIL_LINES;
  return parsed;
}

function quoteShellArg(value: string): string {
  if (value.length === 0) return "''";
  if (!/[^A-Za-z0-9_.,:/@=-]/.test(value)) return value;
  return `'${value.replace(/'/g, `'\\''`)}'`;
}

function buildPtyCommand(argv: string[]): string[] {
  const command = argv.map(quoteShellArg).join(" ");
  const prelude = `stty rows ${DEFAULT_PTY_ROWS} cols ${DEFAULT_PTY_COLS}; `;
  return ["script", "-q", "-e", "-c", `${prelude}${command}`, "/dev/null"];
}

async function runNtm(api: OpenClawPluginApi, argv: string[]): Promise<NtmResult> {
  try {
    return await api.runtime.system.runCommandWithTimeout(buildPtyCommand(argv), {
      timeoutMs: getTimeoutMs(),
    });
  } catch {
    return await api.runtime.system.runCommandWithTimeout(argv, {
      timeoutMs: getTimeoutMs(),
    });
  }
}

async function readState(): Promise<NtmQuickState> {
  try {
    const raw = await readFile(NTM_QUICK_STATE_PATH, "utf8");
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return {};
    const project = typeof (parsed as NtmQuickState).project === "string"
      ? (parsed as NtmQuickState).project.trim()
      : "";
    return project ? { project } : {};
  } catch (error) {
    const err = error as { code?: string };
    if (err.code === "ENOENT") return {};
    throw error;
  }
}

async function writeState(state: NtmQuickState): Promise<void> {
  await writeFile(NTM_QUICK_STATE_PATH, `${JSON.stringify(state, null, 2)}\n`, "utf8");
}

function safeString(value: unknown): string {
  if (typeof value === "string") return value;
  if (value === null || value === undefined) return "";
  return String(value);
}

function parsePaneKey(value: string): number {
  const num = Number.parseInt(value, 10);
  return Number.isFinite(num) ? num : Number.MAX_SAFE_INTEGER;
}

function linesFromUnknown(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map((entry) => {
    if (typeof entry === "string") return entry;
    if (entry && typeof entry === "object") {
      const row = entry as { text?: unknown; line?: unknown };
      if (typeof row.text === "string") return row.text;
      if (typeof row.line === "string") return row.line;
    }
    return safeString(entry);
  });
}

function extractTailPayloadLines(payload: unknown): string[] {
  if (!payload || typeof payload !== "object") return [];
  const asRecord = payload as Record<string, unknown>;

  const directLines = linesFromUnknown(asRecord.lines);
  if (directLines.length > 0) return directLines;

  const panesValue = asRecord.panes;
  if (!panesValue || typeof panesValue !== "object") return [];

  const panes = panesValue as Record<string, unknown>;
  const paneEntries = Object.entries(panes).sort(([a], [b]) => parsePaneKey(a) - parsePaneKey(b));

  const merged: string[] = [];
  for (const [, paneData] of paneEntries) {
    if (!paneData || typeof paneData !== "object") continue;
    const paneRecord = paneData as Record<string, unknown>;
    merged.push(...linesFromUnknown(paneRecord.lines));
  }
  return merged;
}

function parseTailLines(raw: string): string[] {
  const trimmed = normalizeOutput(raw).trim();
  if (!trimmed) return [];

  const parseCandidates = [trimmed];
  const firstBrace = trimmed.indexOf("{");
  const lastBrace = trimmed.lastIndexOf("}");
  if (firstBrace >= 0 && lastBrace > firstBrace) {
    parseCandidates.push(trimmed.slice(firstBrace, lastBrace + 1));
  }

  for (const candidate of parseCandidates) {
    try {
      const parsed = JSON.parse(candidate);
      return extractTailPayloadLines(parsed);
    } catch {
      // try next candidate
    }
  }

  return [];
}

function lastMessageLine(message: string): string {
  const parts = normalizeOutput(message)
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  return parts.at(-1) ?? "";
}

function normalizeMessageLines(message: string): string[] {
  return normalizeOutput(message)
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function normalizeForCompare(value: string): string {
  return normalizeOutput(value).trim();
}

function linesEqual(a: string[], b: string[]): boolean {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i += 1) {
    if (a[i] !== b[i]) return false;
  }
  return true;
}

function normalizePromptLine(line: string): string {
  return normalizeForCompare(line).replace(NO_OUTPUT_CHEVRON_RE, "").trim();
}

function lineMatchesMessageValue(candidate: string, expected: string): boolean {
  if (!candidate || !expected) return false;
  if (candidate === expected) return true;
  if (candidate.includes(expected)) return true;
  if (expected.length > 48 && expected.includes(candidate)) return true;
  return false;
}

function isAssistantOutputLine(value: string): boolean {
  return /^([•◦])\s*/.test(value);
}

function promptMatchesMessageAt(lines: string[], startIndex: number, message: string): boolean {
  const messageLines = normalizeMessageLines(message);
  if (messageLines.length === 0) return false;

  const firstPromptLine = normalizePromptLine(lines[startIndex] ?? "");
  if (!lineMatchesMessageValue(firstPromptLine, messageLines[0]!)) {
    return false;
  }

  if (messageLines.length === 1) return true;

  let messageIndex = 1;
  for (let i = startIndex + 1; i < lines.length && messageIndex < messageLines.length; i += 1) {
    const rawLine = lines[i] ?? "";
    const value = normalizeForCompare(rawLine);

    if (!value) continue;
    if (NO_OUTPUT_CHEVRON_RE.test(normalizeOutput(rawLine))) return false;
    if (NO_OUTPUT_CONTEXT_HINT_RE.test(value)) continue;
    if (NO_OUTPUT_RULE_RE.test(value)) continue;
    if (NO_OUTPUT_ACTIVITY_RE.test(value)) continue;
    if (NO_OUTPUT_PROMPT_RE.test(value)) continue;
    if (isAssistantOutputLine(value)) return false;

    if (!lineMatchesMessageValue(value, messageLines[messageIndex]!)) {
      return false;
    }
    messageIndex += 1;
  }

  return messageIndex === messageLines.length;
}

function messagePromptIndices(lines: string[], message: string): number[] {
  const messageLines = normalizeMessageLines(message);
  if (messageLines.length === 0) return [];

  const indices: number[] = [];
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i] ?? "";
    if (!NO_OUTPUT_CHEVRON_RE.test(normalizeOutput(line))) continue;
    if (promptMatchesMessageAt(lines, i, message)) {
      indices.push(i);
    }
  }
  return indices;
}

function responseLinesForPrompt(lines: string[], promptIndex: number, messageLastLine: string): string[] {
  const block: string[] = [];
  for (let i = promptIndex + 1; i < lines.length; i += 1) {
    const line = lines[i] ?? "";
    if (NO_OUTPUT_CHEVRON_RE.test(normalizeOutput(line))) break;
    block.push(line);
  }
  return filterNoOutputLines(block, messageLastLine);
}

function extractLatestMessageResponse(
  lines: string[],
  message: string,
  messageLastLine: string,
): {
  promptCount: number;
  responseLines: string[];
} {
  const indices = messagePromptIndices(lines, message);
  if (indices.length === 0) {
    return { promptCount: 0, responseLines: [] };
  }
  const latestPrompt = indices[indices.length - 1]!;
  return {
    promptCount: indices.length,
    responseLines: responseLinesForPrompt(lines, latestPrompt, messageLastLine),
  };
}

function filterNoOutputLines(lines: string[], messageLastLine: string): string[] {
  const normalizedMsg = normalizeForCompare(messageLastLine);

  return lines.filter((line) => {
    const value = normalizeForCompare(line);
    if (!value) return false;
    if (NO_OUTPUT_PROMPT_RE.test(value)) return false;
    if (NO_OUTPUT_CHEVRON_RE.test(value)) return false;
    if (NO_OUTPUT_CONTEXT_HINT_RE.test(value)) return false;
    if (NO_OUTPUT_RULE_RE.test(value)) return false;
    if (NO_OUTPUT_ACTIVITY_RE.test(value)) return false;
    if (normalizedMsg) {
      if (value === normalizedMsg) return false;
      if (value.includes(normalizedMsg) && !isAssistantOutputLine(value)) return false;
    }
    return true;
  });
}

function withSendTerminator(msg: string): string {
  const base = normalizeOutput(msg).replace(/\n*$/u, "");
  return `${base}\n\n`;
}

function errorText(prefix: string, result: NtmResult): string {
  const stdout = normalizeOutput(result.stdout ?? "").trim();
  const stderr = normalizeOutput(result.stderr ?? "").trim();
  const exit = result.code && result.code !== 0 ? ` (exit ${result.code})` : "";
  const details = stderr || stdout || "no output";
  return `${prefix}${exit}: ${details}`;
}

async function handleList(api: OpenClawPluginApi): Promise<{ text: string }> {
  try {
    const result = await runNtm(api, ["ntm", "list"]);
    if (result.code && result.code !== 0) {
      return { text: errorText("Error running ntm list", result) };
    }

    const stdout = normalizeOutput(result.stdout ?? "").trim();
    const stderr = normalizeOutput(result.stderr ?? "").trim();
    return { text: stdout || stderr || "No tmux sessions found." };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return { text: `Error running ntm list: ${message}` };
  }
}

async function handleAssign(rawArgs: string): Promise<{ text: string }> {
  const project = rawArgs.trim();
  if (!project) {
    const current = await readState();
    if (current.project) return { text: `Current project: ${current.project}` };
    return { text: "Usage: /na <project>" };
  }

  await writeState({ project });
  return { text: `Saved ntm project: ${project}` };
}

async function runTail(api: OpenClawPluginApi, project: string): Promise<NtmResult> {
  return runTailWithLines(api, project, getRobotTailLines());
}

async function runTailWithLines(
  api: OpenClawPluginApi,
  project: string,
  lines: number,
): Promise<NtmResult> {
  return runNtm(api, [
    "ntm",
    `--robot-tail=${project}`,
    "--panes=2",
    `--lines=${lines}`,
    "--json",
  ]);
}

async function runSend(api: OpenClawPluginApi, project: string, msg: string): Promise<NtmResult> {
  const sendPayload = withSendTerminator(msg);
  return runNtm(api, [
    "ntm",
    `--robot-send=${project}`,
    "--panes=2",
    "--track",
    `--msg=${sendPayload}`,
  ]);
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function pollRobotTailUntilResponse(
  api: OpenClawPluginApi,
  params: {
    project: string;
    baseline: string[];
    message: string;
    messageLastLine: string;
    timeoutMs: number;
    pollIntervalMs: number;
  },
): Promise<RobotPollResult> {
  const start = Date.now();
  const baselineMatch = extractLatestMessageResponse(
    params.baseline,
    params.message,
    params.messageLastLine,
  );
  while (Date.now() - start < params.timeoutMs) {
    const tailResult = await runTail(api, params.project);
    if (tailResult.code && tailResult.code !== 0) {
      return { error: errorText("Error polling robot tail", tailResult) };
    }

    const lines = parseTailLines(`${tailResult.stdout ?? ""}${tailResult.stderr ?? ""}`);
    const currentMatch = extractLatestMessageResponse(lines, params.message, params.messageLastLine);
    if (currentMatch.responseLines.length > 0) {
      const hasNewPrompt = currentMatch.promptCount > baselineMatch.promptCount;
      const responseChanged = !linesEqual(currentMatch.responseLines, baselineMatch.responseLines);
      const snapshotChanged = !linesEqual(lines, params.baseline);
      if (hasNewPrompt || responseChanged || snapshotChanged) {
        return { response: currentMatch.responseLines.join("\n") };
      }
    }

    await sleep(params.pollIntervalMs);
  }

  return { timedOut: true };
}

async function resolveSendRequest(rawArgs: string): Promise<{
  message?: string;
  project?: string;
  error?: string;
}> {
  const message = rawArgs.trim();
  if (!message) {
    return { error: "Usage: /ns <message>" };
  }

  const state = await readState();
  const project = state.project?.trim();
  if (!project) {
    return { error: "No ntm project saved. Run /na <project> first." };
  }

  return { message, project };
}

function parseNCatLines(rawArgs: string): { lines?: number; error?: string } {
  const trimmed = rawArgs.trim();
  if (!trimmed) {
    return { lines: DEFAULT_NCAT_LINES };
  }

  const { token, rest } = splitFirstToken(trimmed);
  if (!token || rest) {
    return { error: "Usage: /nc [lines]" };
  }

  const lines = Number.parseInt(token, 10);
  if (!Number.isFinite(lines) || lines <= 0) {
    return { error: "Usage: /nc [lines] (lines must be a positive integer)." };
  }

  return { lines };
}

function formatNCatLines(lines: string[]): string[] {
  return lines.filter((line) => {
    const value = normalizeForCompare(line);
    if (!value) return false;
    if (NO_OUTPUT_CONTEXT_HINT_RE.test(value)) return false;
    if (NO_OUTPUT_RULE_RE.test(value)) return false;
    if (NO_OUTPUT_ACTIVITY_RE.test(value)) return false;
    return true;
  });
}

async function handleCat(api: OpenClawPluginApi, rawArgs: string): Promise<{ text: string }> {
  const parsed = parseNCatLines(rawArgs);
  if (parsed.error) {
    return { text: parsed.error };
  }

  const state = await readState();
  const project = state.project?.trim();
  if (!project) {
    return { text: "No ntm project saved. Run /na <project> first." };
  }

  const tailResult = await runTailWithLines(api, project, parsed.lines ?? DEFAULT_NCAT_LINES);
  if (tailResult.code && tailResult.code !== 0) {
    return { text: errorText("Error reading robot tail", tailResult) };
  }

  const rawCombined = normalizeOutput(`${tailResult.stdout ?? ""}${tailResult.stderr ?? ""}`);
  const parsedLines = parseTailLines(rawCombined);

  if (parsedLines.length > 0) {
    const output = formatNCatLines(parsedLines);
    if (output.length === 0) {
      return { text: `No output found in pane 2 for ${project}.` };
    }
    return { text: output.join("\n") };
  }

  const fallback = rawCombined.trim();
  if (fallback) {
    return { text: fallback };
  }

  return { text: `No output found in pane 2 for ${project}.` };
}

async function resolveRobotTailBaseline(api: OpenClawPluginApi, project: string): Promise<string[]> {
  try {
    const baselineResult = await runTail(api, project);
    if (!baselineResult.code || baselineResult.code === 0) {
      return parseTailLines(`${baselineResult.stdout ?? ""}${baselineResult.stderr ?? ""}`);
    }
  } catch {
    // Ignore baseline failure and continue.
  }
  return [];
}

async function handleSendAndPoll(api: OpenClawPluginApi, rawArgs: string): Promise<{ text: string }> {
  const prepared = await resolveSendRequest(rawArgs);
  if (prepared.error) {
    return { text: prepared.error };
  }

  const message = prepared.message ?? "";
  const project = prepared.project ?? "";
  const msgLastLine = lastMessageLine(message);
  const pollIntervalMs = getPollIntervalMs();
  const timeoutMs = getTimeoutMs();
  const baseline = await resolveRobotTailBaseline(api, project);

  const sendResult = await runSend(api, project, message);
  if (sendResult.code && sendResult.code !== 0) {
    return { text: errorText("Error sending robot message", sendResult) };
  }

  const pollResult = await pollRobotTailUntilResponse(api, {
    project,
    baseline,
    message,
    messageLastLine: msgLastLine,
    timeoutMs,
    pollIntervalMs,
  });
  if (pollResult.error) {
    return { text: pollResult.error };
  }
  if (pollResult.response) {
    return { text: pollResult.response };
  }

  return { text: `Timed out after ${Math.floor(timeoutMs / 1000)}s waiting for response from ${project}.` };
}

async function handleSendAndPollAsync(
  api: OpenClawPluginApi,
  ctx: CommandInvocationContext,
): Promise<{ text: string }> {
  const prepared = await resolveSendRequest(ctx.args ?? "");
  if (prepared.error) {
    return { text: prepared.error };
  }

  const message = prepared.message ?? "";
  const project = prepared.project ?? "";
  const msgLastLine = lastMessageLine(message);
  const pollIntervalMs = getPollIntervalMs();
  const timeoutMs = getTimeoutMs();
  const baseline = await resolveRobotTailBaseline(api, project);

  const sendResult = await runSend(api, project, message);
  if (sendResult.code && sendResult.code !== 0) {
    return { text: errorText("Error sending robot message", sendResult) };
  }

  const origin = resolveAsyncReplyOrigin(ctx);
  const target = resolveAsyncReplyTarget(origin);
  if (!target) {
    return { text: "Unable to resolve reply target for async send." };
  }

  void (async () => {
    try {
      const pollResult = await pollRobotTailUntilResponse(api, {
        project,
        baseline,
        message,
        messageLastLine: msgLastLine,
        timeoutMs,
        pollIntervalMs,
      });
      const finalText =
        pollResult.response ||
        pollResult.error ||
        `Timed out after ${Math.floor(timeoutMs / 1000)}s waiting for response from ${project}.`;
      await sendAsyncReply(api, origin, finalText);
    } catch (error) {
      const messageText = error instanceof Error ? error.message : String(error);
      api.logger.error(`nsa async follow-up failed: ${messageText}`);
    }
  })();

  return { text: `Message sent to ${project}, waiting for result...` };
}

export default function register(api: OpenClawPluginApi) {
  const commandDef = {
    acceptsArgs: true,
    requireAuth: true,
  };

  api.registerCommand({
    ...commandDef,
    name: "nl",
    description: "Run ntm list.",
    handler: async () => handleList(api),
  });

  api.registerCommand({
    ...commandDef,
    name: "na",
    description: "Save ntm project for /ns and /nsa.",
    handler: async (ctx: { args?: string }) => handleAssign(ctx.args ?? ""),
  });

  api.registerCommand({
    ...commandDef,
    name: "nc",
    description: "Show recent pane-2 output for saved ntm project (/n-cat).",
    handler: async (ctx: { args?: string }) => handleCat(api, ctx.args ?? ""),
  });

  api.registerCommand({
    ...commandDef,
    name: "ns",
    description: "Send message to saved ntm project and poll for response.",
    handler: async (ctx: { args?: string }) => handleSendAndPoll(api, ctx.args ?? ""),
  });

  api.registerCommand({
    ...commandDef,
    name: "nsa",
    description: "Async send to saved ntm project; reply posts later to same channel context.",
    handler: async (ctx: CommandInvocationContext) => handleSendAndPollAsync(api, ctx),
  });
}
