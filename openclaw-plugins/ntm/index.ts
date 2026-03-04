import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { readFile, writeFile } from "node:fs/promises";
import { homedir } from "node:os";
import { join } from "node:path";

const DEFAULT_TIMEOUT_MS = 10_000;
const DEFAULT_PTY_ROWS = 40;
const DEFAULT_PTY_COLS = 120;
const QUICK_COMMANDS_PATH =
  process.env.CLAWD_RUN_COMMANDS_FILE?.trim() ||
  join(homedir(), ".clawd-run-commands.md");
const QUICK_STORE_VERSION = 1;
const LABEL_PATTERN = /^[A-Za-z0-9_-]+$/;
const FIXES_PATH =
  process.env.CLAWD_NTM_FIXES_FILE?.trim() ||
  join(homedir(), ".clawd-ntm-fixes.json");

type QuickStore = Record<string, Record<string, string>>;
type FixStore = Record<string, string>; // position number (as string) → fixed value

type CommandOption = {
  key: string;
  usage: (commandName: string) => string;
  description: string;
  handler: (rest: string) => Promise<{ text: string }>;
};

function wrapCodeBlock(text: string): string {
  return `\`\`\`\n${text}\n\`\`\``;
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

function parseLabelAndCommand(input: string): { label: string; command: string } | null {
  const trimmed = input.trim();
  if (!trimmed) return null;

  const firstWhitespace = trimmed.search(/\s/);
  if (firstWhitespace === -1) {
    return { label: trimmed, command: "" };
  }

  return {
    label: trimmed.slice(0, firstWhitespace),
    command: trimmed.slice(firstWhitespace).trim(),
  };
}

function parseShellArgs(raw: string): string[] {
  const args: string[] = [];
  let current = "";
  let quote: "'" | '"' | null = null;
  let escape = false;

  for (const char of raw) {
    if (escape) {
      current += char;
      escape = false;
      continue;
    }

    if (char === "\\" && quote !== "'") {
      escape = true;
      continue;
    }

    if (quote) {
      if (char === quote) {
        quote = null;
      } else {
        current += char;
      }
      continue;
    }

    if (char === "'" || char === '"') {
      quote = char;
      continue;
    }

    if (/\s/.test(char)) {
      if (current) {
        args.push(current);
        current = "";
      }
      continue;
    }

    current += char;
  }

  if (current) args.push(current);
  return args;
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

async function runNtm(api: OpenClawPluginApi, argv: string[]) {
  try {
    return await api.runtime.system.runCommandWithTimeout(buildPtyCommand(argv), {
      timeoutMs: DEFAULT_TIMEOUT_MS,
    });
  } catch {
    return await api.runtime.system.runCommandWithTimeout(argv, {
      timeoutMs: DEFAULT_TIMEOUT_MS,
    });
  }
}

function normalizeOutput(text: string): string {
  return text.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
}

function sanitizeQuickStore(value: unknown): QuickStore {
  if (!value || typeof value !== "object") return {};

  const input = value as Record<string, unknown>;
  const output: QuickStore = {};

  for (const [scope, scopeValue] of Object.entries(input)) {
    if (!scopeValue || typeof scopeValue !== "object") continue;
    const commands: Record<string, string> = {};

    for (const [label, command] of Object.entries(scopeValue as Record<string, unknown>)) {
      if (typeof label !== "string" || typeof command !== "string") continue;
      const normalizedLabel = label.trim();
      const normalizedCommand = command.trim();
      if (!normalizedLabel || !normalizedCommand) continue;
      commands[normalizedLabel] = normalizedCommand;
    }

    if (Object.keys(commands).length > 0) output[scope] = commands;
  }

  return output;
}

function parseQuickStoreMarkdown(markdown: string): QuickStore {
  const jsonBlockMatch = markdown.match(/```json\s*([\s\S]*?)\s*```/i);
  if (!jsonBlockMatch) return {};

  try {
    const parsed = JSON.parse(jsonBlockMatch[1]);
    if (parsed && typeof parsed === "object") {
      const container = parsed as Record<string, unknown>;
      if (container.commands && typeof container.commands === "object") {
        return sanitizeQuickStore(container.commands);
      }
      return sanitizeQuickStore(container);
    }
    return {};
  } catch {
    return {};
  }
}

function sortCommandMap(commands: Record<string, string>): Record<string, string> {
  return Object.fromEntries(
    Object.entries(commands).sort(([a], [b]) =>
      a.localeCompare(b, "en", { sensitivity: "base" }),
    ),
  );
}

function sortQuickStore(store: QuickStore): QuickStore {
  return Object.fromEntries(
    Object.entries(store)
      .sort(([a], [b]) => a.localeCompare(b, "en", { sensitivity: "base" }))
      .map(([scope, commands]) => [scope, sortCommandMap(commands)]),
  );
}

function renderScopePreview(scopeCommands: Record<string, string>): string[] {
  const entries = Object.entries(scopeCommands).sort(([a], [b]) =>
    a.localeCompare(b, "en", { sensitivity: "base" }),
  );

  if (entries.length === 0) return ["- (none)"];

  return entries.map(([label, command]) => `- \`${label}\` → \`${command}\``);
}

function serializeQuickStoreMarkdown(store: QuickStore): string {
  const normalizedStore = sortQuickStore(store);
  const payload = {
    version: QUICK_STORE_VERSION,
    commands: normalizedStore,
  };

  return [
    "# Clawd quick commands",
    "",
    "Managed by the /run and /ntm plugins.",
    "",
    "```json",
    JSON.stringify(payload, null, 2),
    "```",
    "",
    "## run",
    ...renderScopePreview(normalizedStore.run ?? {}),
    "",
    "## ntm",
    ...renderScopePreview(normalizedStore.ntm ?? {}),
    "",
  ].join("\n");
}

async function readQuickStore(): Promise<QuickStore> {
  try {
    const markdown = await readFile(QUICK_COMMANDS_PATH, "utf8");
    return parseQuickStoreMarkdown(markdown);
  } catch (error) {
    const err = error as { code?: string };
    if (err.code === "ENOENT") return {};
    throw error;
  }
}

async function writeQuickStore(store: QuickStore): Promise<void> {
  const markdown = serializeQuickStoreMarkdown(store);
  await writeFile(QUICK_COMMANDS_PATH, markdown, "utf8");
}

function validateLabel(label: string): string | null {
  if (!label) return "Missing label.";
  if (!LABEL_PATTERN.test(label)) {
    return "Label must be one word using letters, numbers, dashes, or underscores.";
  }
  return null;
}

function normalizeStoredCommand(command: string): string {
  const trimmed = command.trim();
  if (!trimmed) return "";
  if (/^ntm(\s+|$)/i.test(trimmed)) {
    return trimmed.replace(/^ntm\s*/i, "").trim();
  }
  return trimmed;
}

function materializeCommand(command: string): string {
  const normalized = normalizeStoredCommand(command);
  return normalized.toLowerCase().startsWith("ntm ") ? normalized : `ntm ${normalized}`;
}

function getTemplateIndexes(template: string): number[] {
  const indexes = new Set<number>();
  const matches = template.matchAll(/\{(\d+)\}/g);

  for (const match of matches) {
    const index = Number.parseInt(match[1], 10);
    if (Number.isInteger(index) && index > 0) {
      indexes.add(index);
    }
  }

  return [...indexes].sort((a, b) => a - b);
}

function applyPositionalTemplate(
  template: string,
  args: string[],
): { command?: string; error?: string } {
  const indexes = getTemplateIndexes(template);

  if (indexes.length === 0) {
    if (args.length > 0) {
      return { error: "This quick command does not accept positional arguments." };
    }
    return { command: template };
  }

  const missing = indexes.filter((index) => index > args.length);
  if (missing.length > 0) {
    const placeholders = missing.map((index) => `{${index}}`).join(", ");
    return { error: `Missing required argument(s): ${placeholders}.` };
  }

  const extras = args
    .map((_, idx) => idx + 1)
    .filter((position) => !indexes.includes(position));

  if (extras.length > 0) {
    const positions = extras.map((idx) => `{${idx}}`).join(", ");
    return { error: `Too many positional arguments. No placeholder for: ${positions}.` };
  }

  const command = template.replace(/\{(\d+)\}/g, (full, capture) => {
    const index = Number.parseInt(capture, 10);
    if (!Number.isInteger(index) || index < 1) return full;
    return args[index - 1] ?? full;
  });

  return { command };
}

async function readFixes(): Promise<FixStore> {
  try {
    const content = await readFile(FIXES_PATH, "utf8");
    const parsed = JSON.parse(content);
    if (!parsed || typeof parsed !== "object") return {};
    const result: FixStore = {};
    for (const [key, value] of Object.entries(parsed)) {
      const num = Number.parseInt(key, 10);
      if (Number.isInteger(num) && num > 0 && typeof value === "string") {
        result[String(num)] = value as string;
      }
    }
    return result;
  } catch {
    return {};
  }
}

async function writeFixes(fixes: FixStore): Promise<void> {
  await writeFile(FIXES_PATH, JSON.stringify(fixes, null, 2), "utf8");
}

function applyPositionalTemplateWithFixes(
  template: string,
  userArgs: string[],
  fixes: FixStore,
): { command?: string; error?: string } {
  const indexes = getTemplateIndexes(template);

  if (indexes.length === 0) {
    if (userArgs.length > 0) {
      return { error: "This quick command does not accept positional arguments." };
    }
    return { command: template };
  }

  // Determine which template positions have fixes
  const fixedPositions = new Set<number>();
  for (const idx of indexes) {
    if (fixes[String(idx)] !== undefined) {
      fixedPositions.add(idx);
    }
  }

  const unfixedPositions = indexes.filter((idx) => !fixedPositions.has(idx));

  // User args fill unfixed positions in order
  if (userArgs.length < unfixedPositions.length) {
    const missing = unfixedPositions
      .slice(userArgs.length)
      .map((idx) => `{${idx}}`)
      .join(", ");
    return { error: `Missing required argument(s): ${missing}.` };
  }

  if (userArgs.length > unfixedPositions.length) {
    const expected = unfixedPositions.length;
    const fixedCount = fixedPositions.size;
    return {
      error: `Too many arguments. Expected ${expected} (${fixedCount} fixed), got ${userArgs.length}.`,
    };
  }

  // Build full args array
  const maxIdx = Math.max(...indexes);
  const fullArgs: string[] = new Array(maxIdx).fill("");

  let userArgIdx = 0;
  for (const idx of indexes) {
    if (fixedPositions.has(idx)) {
      fullArgs[idx - 1] = fixes[String(idx)];
    } else {
      fullArgs[idx - 1] = userArgs[userArgIdx++];
    }
  }

  // Apply template substitution
  const command = template.replace(/\{(\d+)\}/g, (full, capture) => {
    const index = Number.parseInt(capture, 10);
    if (!Number.isInteger(index) || index < 1 || index > maxIdx) return full;
    return fullArgs[index - 1] ?? full;
  });

  return { command };
}

async function saveQuickCommand(
  label: string,
  command: string,
): Promise<{ created: boolean; normalizedCommand: string }> {
  const store = await readQuickStore();
  const scopeCommands = { ...(store.ntm ?? {}) };
  const created = !(label in scopeCommands);

  scopeCommands[label] = normalizeStoredCommand(command);
  store.ntm = scopeCommands;
  await writeQuickStore(store);

  return { created, normalizedCommand: scopeCommands[label] };
}

async function removeQuickCommand(label: string): Promise<boolean> {
  const store = await readQuickStore();
  const scopeCommands = { ...(store.ntm ?? {}) };

  if (!(label in scopeCommands)) return false;

  delete scopeCommands[label];

  if (Object.keys(scopeCommands).length === 0) {
    delete store.ntm;
  } else {
    store.ntm = scopeCommands;
  }

  await writeQuickStore(store);
  return true;
}

async function listQuickCommands(): Promise<Record<string, string>> {
  const store = await readQuickStore();
  return { ...(store.ntm ?? {}) };
}

function renderQuickList(commandName: string, commands: Record<string, string>): string {
  const entries = Object.entries(commands).sort(([a], [b]) =>
    a.localeCompare(b, "en", { sensitivity: "base" }),
  );

  if (entries.length === 0) {
    return `No quick commands saved for /${commandName}. Add one with /${commandName} +q <label> <command>.`;
  }

  const lines = [`Quick commands for /${commandName}:`];
  for (const [label, command] of entries) {
    lines.push(`- \`${label}\` → \`${materializeCommand(command)}\``);
  }
  return lines.join("\n");
}

async function executeNtmCommand(api: OpenClawPluginApi, command: string): Promise<{ text: string }> {
  const argv = parseShellArgs(normalizeStoredCommand(command));
  if (argv.length === 0) {
    return { text: "Command cannot be empty." };
  }

  try {
    const result = await runNtm(api, ["ntm", ...argv]);
    const combined = normalizeOutput(`${result.stdout ?? ""}${result.stderr ?? ""}`);
    const output = combined.trim();

    if (result.code && result.code !== 0) {
      const failure = output || `ntm exited with code ${result.code}`;
      return { text: wrapCodeBlock(failure) };
    }

    return { text: wrapCodeBlock(output || "(no output)") };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return { text: `Error running ntm: ${message}` };
  }
}

function buildHelpText(commandName: string, options: CommandOption[]): string {
  const lines = [`/${commandName} options:`];
  for (const option of options) {
    lines.push(`- ${option.usage(commandName)} — ${option.description}`);
  }
  lines.push(`- Placeholders: use {1}, {2}, ... in quick command templates.`);
  lines.push(`- Quick commands file: \`${QUICK_COMMANDS_PATH}\``);
  return lines.join("\n");
}

function createOptions(api: OpenClawPluginApi, commandName: string): CommandOption[] {
  return [
    {
      key: "help",
      usage: (name) => `/${name} help`,
      description: "Show available options.",
      handler: async () => ({ text: "" }),
    },
    {
      key: "list",
      usage: (name) => `/${name} list`,
      description: "List tmux sessions using ntm.",
      handler: async (rest) => {
        if (rest.length > 0) return { text: `Usage: /${commandName} list` };

        try {
          const result = await runNtm(api, ["ntm", "list"]);
          const stdout = normalizeOutput(result.stdout ?? "").trim();
          const stderr = normalizeOutput(result.stderr ?? "").trim();

          if (result.code && result.code !== 0) {
            return {
              text: `Error: ${stderr || stdout || `ntm list exited with code ${result.code}`}`,
            };
          }

          if (!stdout) return { text: stderr || "No tmux sessions found." };
          return { text: stdout };
        } catch (err) {
          const message = err instanceof Error ? err.message : String(err);
          return { text: `Error running ntm list: ${message}` };
        }
      },
    },
    {
      key: "run",
      usage: (name) => `/${name} run <args>`,
      description: "Run an arbitrary ntm command.",
      handler: async (rest) => {
        if (!rest) return { text: `Usage: /${commandName} run <args>` };
        return executeNtmCommand(api, rest);
      },
    },
    {
      key: "+q",
      usage: (name) => `/${name} +q <label> <command>`,
      description:
        "Add an ntm quick command template (or overwrite existing label). Supports {1}, {2}, ... placeholders.",
      handler: async (rest) => {
        const parsed = parseLabelAndCommand(rest);
        if (!parsed || !parsed.command) {
          return { text: `Usage: /${commandName} +q <label> <command>` };
        }

        const labelError = validateLabel(parsed.label);
        if (labelError) return { text: labelError };

        const normalizedCommand = normalizeStoredCommand(parsed.command);
        if (!normalizedCommand) return { text: "Command cannot be empty." };

        const { created } = await saveQuickCommand(parsed.label, normalizedCommand);
        const action = created ? "Saved" : "Updated";

        return {
          text: `${action} quick command \`${parsed.label}\` → \`${materializeCommand(normalizedCommand)}\`.`,
        };
      },
    },
    {
      key: "-q",
      usage: (name) => `/${name} -q <label>`,
      description: "Delete an ntm quick command.",
      handler: async (rest) => {
        const { token: label, rest: extra } = splitFirstToken(rest);
        if (!label || extra) return { text: `Usage: /${commandName} -q <label>` };

        const labelError = validateLabel(label);
        if (labelError) return { text: labelError };

        const deleted = await removeQuickCommand(label);
        if (!deleted) return { text: `No quick command found for label \`${label}\`.` };

        return { text: `Deleted quick command \`${label}\`.` };
      },
    },
    {
      key: "q",
      usage: (name) => `/${name} q [<label> [args...]]`,
      description: "List quick commands, or execute one by label with positional arguments. Fixed placeholders (see +qf) are applied automatically.",
      handler: async (rest) => {
        const { token: label, rest: argText } = splitFirstToken(rest);

        if (!label) {
          const commands = await listQuickCommands();
          return { text: renderQuickList(commandName, commands) };
        }

        const labelError = validateLabel(label);
        if (labelError) return { text: labelError };

        const commands = await listQuickCommands();
        const stored = commands[label];
        if (!stored) {
          return { text: `No quick command found for label \`${label}\`.` };
        }

        const positionalArgs = argText ? parseShellArgs(argText) : [];
        const fixes = await readFixes();
        const rendered = applyPositionalTemplateWithFixes(stored, positionalArgs, fixes);
        if (rendered.error) return { text: rendered.error };

        return executeNtmCommand(api, rendered.command ?? stored);
      },
    },
    {
      key: "+qf",
      usage: (name) => `/${name} +qf <number> <value>`,
      description: "Fix a placeholder position to a value for all subsequent quick commands.",
      handler: async (rest) => {
        const { token: numStr, rest: value } = splitFirstToken(rest);
        if (!numStr || !value) {
          return { text: `Usage: /${commandName} +qf <number> <value>` };
        }
        const num = Number.parseInt(numStr, 10);
        if (!Number.isInteger(num) || num < 1) {
          return { text: "Position must be a positive integer." };
        }
        const fixes = await readFixes();
        fixes[String(num)] = value;
        await writeFixes(fixes);
        return { text: `Fixed placeholder {${num}} → \`${value}\`.` };
      },
    },
    {
      key: "-qf",
      usage: (name) => `/${name} -qf <number>`,
      description: "Clear a fixed placeholder.",
      handler: async (rest) => {
        const { token: numStr, rest: extra } = splitFirstToken(rest);
        if (!numStr || extra) {
          return { text: `Usage: /${commandName} -qf <number>` };
        }
        const num = Number.parseInt(numStr, 10);
        if (!Number.isInteger(num) || num < 1) {
          return { text: "Position must be a positive integer." };
        }
        const fixes = await readFixes();
        if (!(String(num) in fixes)) {
          return { text: `No fix set for placeholder {${num}}.` };
        }
        delete fixes[String(num)];
        await writeFixes(fixes);
        return { text: `Cleared fix for placeholder {${num}}.` };
      },
    },
    {
      key: "qf",
      usage: (name) => `/${name} qf`,
      description: "List all fixed placeholders.",
      handler: async (rest) => {
        if (rest) return { text: `Usage: /${commandName} qf` };
        const fixes = await readFixes();
        const entries = Object.entries(fixes).sort(
          ([a], [b]) => Number.parseInt(a, 10) - Number.parseInt(b, 10),
        );
        if (entries.length === 0) {
          return { text: "No placeholder fixes set." };
        }
        const lines = ["Fixed placeholders:"];
        for (const [pos, value] of entries) {
          lines.push(`- {${pos}} → \`${value}\``);
        }
        return { text: lines.join("\n") };
      },
    },
  ];
}

export default function register(api: OpenClawPluginApi) {
  function makeHandler(commandName: string) {
    return async (ctx: { args?: string }) => {
      const rawArgs = (ctx.args ?? "").trim() || "list";

      const options = createOptions(api, commandName);
      const optionByKey = new Map(options.map((option) => [option.key, option]));
      const { token, rest } = splitFirstToken(rawArgs);

      const matchedOption = optionByKey.get(token);
      if (!matchedOption) {
        return { text: `Usage: /${commandName} [list] | /${commandName} run <args> | /${commandName} help` };
      }

      if (matchedOption.key === "help") {
        return { text: buildHelpText(commandName, options) };
      }

      return matchedOption.handler(rest);
    };
  }

  const commandDef = {
    description: "Run ntm commands and manage ntm quick command shortcuts.",
    acceptsArgs: true,
    requireAuth: true,
  };

  api.registerCommand({ ...commandDef, name: "ntm", handler: makeHandler("ntm") });
  api.registerCommand({ ...commandDef, name: "n", handler: makeHandler("n") });
}
