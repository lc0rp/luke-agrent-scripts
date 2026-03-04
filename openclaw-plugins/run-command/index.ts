import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { execFile } from "node:child_process";
import { readFile, writeFile } from "node:fs/promises";
import { homedir } from "node:os";
import { join } from "node:path";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);
const QUICK_COMMANDS_PATH =
  process.env.CLAWD_RUN_COMMANDS_FILE?.trim() ||
  join(homedir(), ".clawd-run-commands.md");
const QUICK_STORE_VERSION = 1;
const LABEL_PATTERN = /^[A-Za-z0-9_-]+$/;

type QuickScope = "run" | "ntm";
type QuickStore = Record<string, Record<string, string>>;

type CommandOption = {
  key: string;
  usage: (commandName: string) => string;
  description: string;
  handler: (rest: string) => Promise<{ text: string }>;
};

function wrapCodeBlock(text: string): string {
  return `\`\`\`\n${text ?? ""}\n\`\`\``;
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

    if (Object.keys(commands).length > 0) {
      output[scope] = commands;
    }
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

function normalizeStoredCommand(scope: QuickScope, command: string): string {
  const trimmed = command.trim();
  if (scope !== "ntm") return trimmed;
  if (!trimmed) return "";
  if (/^ntm(\s+|$)/i.test(trimmed)) {
    return trimmed.replace(/^ntm\s*/i, "").trim();
  }
  return trimmed;
}

function materializeCommand(scope: QuickScope, command: string): string {
  const normalized = command.trim();
  if (scope !== "ntm") return normalized;
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
    return {
      error: `Missing required argument(s): ${placeholders}.`,
    };
  }

  const extras = args
    .map((_, idx) => idx + 1)
    .filter((position) => !indexes.includes(position));

  if (extras.length > 0) {
    const positions = extras.map((idx) => `{${idx}}`).join(", ");
    return {
      error: `Too many positional arguments. No placeholder for: ${positions}.`,
    };
  }

  const command = template.replace(/\{(\d+)\}/g, (full, capture) => {
    const index = Number.parseInt(capture, 10);
    if (!Number.isInteger(index) || index < 1) return full;
    return args[index - 1] ?? full;
  });

  return { command };
}

function renderQuickList(scope: QuickScope, commandName: string, commands: Record<string, string>): string {
  const entries = Object.entries(commands).sort(([a], [b]) =>
    a.localeCompare(b, "en", { sensitivity: "base" }),
  );

  if (entries.length === 0) {
    return `No quick commands saved for /${commandName}. Add one with /${commandName} +q <label> <command>.`;
  }

  const lines = [`Quick commands for /${commandName}:`];
  for (const [label, command] of entries) {
    const preview = scope === "ntm" ? materializeCommand("ntm", command) : command;
    lines.push(`- \`${label}\` → \`${preview}\``);
  }
  return lines.join("\n");
}

async function saveQuickCommand(
  scope: QuickScope,
  label: string,
  command: string,
): Promise<{ created: boolean; normalizedCommand: string }> {
  const store = await readQuickStore();
  const scopeCommands = { ...(store[scope] ?? {}) };
  const created = !(label in scopeCommands);

  scopeCommands[label] = normalizeStoredCommand(scope, command);
  store[scope] = scopeCommands;
  await writeQuickStore(store);

  return { created, normalizedCommand: scopeCommands[label] };
}

async function removeQuickCommand(scope: QuickScope, label: string): Promise<boolean> {
  const store = await readQuickStore();
  const scopeCommands = { ...(store[scope] ?? {}) };

  if (!(label in scopeCommands)) return false;

  delete scopeCommands[label];

  if (Object.keys(scopeCommands).length === 0) {
    delete store[scope];
  } else {
    store[scope] = scopeCommands;
  }

  await writeQuickStore(store);
  return true;
}

async function listQuickCommands(scope: QuickScope): Promise<Record<string, string>> {
  const store = await readQuickStore();
  return { ...(store[scope] ?? {}) };
}

async function runShellCommand(rawCommand: string): Promise<{ text: string }> {
  const scriptArgs = [
    "-q",
    "-e",
    "-c",
    `stty rows 40 cols 120; ${rawCommand}`,
    "/dev/null",
  ];

  try {
    const { stdout } = await execFileAsync("script", scriptArgs, {
      encoding: "utf8",
      maxBuffer: 10 * 1024 * 1024,
    });
    return { text: wrapCodeBlock(stdout ?? "") };
  } catch (error) {
    const err = error as { stdout?: string; stderr?: string; message?: string };
    let output = "";
    if (typeof err.stdout === "string") output += err.stdout;
    if (typeof err.stderr === "string" && err.stderr.length) {
      output += output ? `\n${err.stderr}` : err.stderr;
    }
    if (!output) output = err.message ?? "Command failed";
    return { text: wrapCodeBlock(output) };
  }
}

function buildHelpText(commandName: string, options: CommandOption[]): string {
  const lines = [`/${commandName} options:`];
  for (const option of options) {
    lines.push(`- ${option.usage(commandName)} — ${option.description}`);
  }

  if (commandName === "run") {
    lines.push(`- /${commandName} <shell command> — execute a command immediately`);
  }

  lines.push(`- Placeholders: use {1}, {2}, ... in quick command templates.`);
  lines.push(`- Quick commands file: \`${QUICK_COMMANDS_PATH}\``);
  return lines.join("\n");
}

function createQuickCommandOptions(scope: QuickScope, commandName: string): CommandOption[] {
  return [
    {
      key: "help",
      usage: (name) => `/${name} help`,
      description: "Show available options.",
      handler: async () => ({ text: "" }),
    },
    {
      key: "+q",
      usage: (name) => `/${name} +q <label> <command>`,
      description:
        "Add a quick command template (or overwrite when the label already exists). Supports {1}, {2}, ... placeholders.",
      handler: async (rest) => {
        const parsed = parseLabelAndCommand(rest);
        if (!parsed || !parsed.command) {
          return { text: `Usage: /${commandName} +q <label> <command>` };
        }

        const labelError = validateLabel(parsed.label);
        if (labelError) return { text: labelError };

        const normalizedCommand = normalizeStoredCommand(scope, parsed.command);
        if (!normalizedCommand) {
          return { text: "Command cannot be empty." };
        }

        const { created } = await saveQuickCommand(scope, parsed.label, normalizedCommand);
        const action = created ? "Saved" : "Updated";
        const displayCommand = materializeCommand(scope, normalizedCommand);

        return {
          text: `${action} quick command \`${parsed.label}\` → \`${displayCommand}\`.`,
        };
      },
    },
    {
      key: "-q",
      usage: (name) => `/${name} -q <label>`,
      description: "Delete a quick command by label.",
      handler: async (rest) => {
        const { token: label, rest: extra } = splitFirstToken(rest);
        if (!label || extra) {
          return { text: `Usage: /${commandName} -q <label>` };
        }

        const labelError = validateLabel(label);
        if (labelError) return { text: labelError };

        const deleted = await removeQuickCommand(scope, label);
        if (!deleted) {
          return { text: `No quick command found for label \`${label}\`.` };
        }

        return { text: `Deleted quick command \`${label}\`.` };
      },
    },
    {
      key: "q",
      usage: (name) => `/${name} q [<label> [args...]]`,
      description: "List quick commands, or execute one by label with positional arguments.",
      handler: async (rest) => {
        const { token: label, rest: argText } = splitFirstToken(rest);

        if (!label) {
          const commands = await listQuickCommands(scope);
          return { text: renderQuickList(scope, commandName, commands) };
        }

        const labelError = validateLabel(label);
        if (labelError) return { text: labelError };

        const commands = await listQuickCommands(scope);
        const stored = commands[label];
        if (!stored) {
          return { text: `No quick command found for label \`${label}\`.` };
        }

        const positionalArgs = argText ? parseShellArgs(argText) : [];
        const rendered = applyPositionalTemplate(stored, positionalArgs);
        if (rendered.error) return { text: rendered.error };

        return runShellCommand(materializeCommand(scope, rendered.command ?? stored));
      },
    },
  ];
}

export default function register(api: OpenClawPluginApi) {
  function makeHandler(commandName: string) {
    return async (ctx: { args?: string }) => {
      const rawArgs = (ctx.args ?? "").trim();
      const options = createQuickCommandOptions("run", commandName);
      const optionByKey = new Map(options.map((option) => [option.key, option]));

      if (!rawArgs) {
        return { text: `Usage: /${commandName} <command> | /${commandName} help` };
      }

      const { token, rest } = splitFirstToken(rawArgs);
      const matchedOption = optionByKey.get(token);

      if (matchedOption) {
        if (matchedOption.key === "help") {
          return { text: buildHelpText(commandName, options) };
        }

        return matchedOption.handler(rest);
      }

      return runShellCommand(rawArgs);
    };
  }

  const commandDef = {
    description: "Run shell commands, and manage quick command shortcuts.",
    acceptsArgs: true,
    requireAuth: true,
  };

  api.registerCommand({ ...commandDef, name: "run", handler: makeHandler("run") });
  api.registerCommand({ ...commandDef, name: "r", handler: makeHandler("r") });
}
