const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const tempRoot = fsSync.mkdtempSync(path.join(os.tmpdir(), "ntm-quick-plugin-test-"));
process.env.CLAWD_NTM_QUICK_STATE_FILE = path.join(tempRoot, "state.json");
process.env.NTM_QUICK_TIMEOUT_MS = "80";
process.env.NTM_QUICK_POLL_INTERVAL_MS = "1";

const jiti = require("/data/projects/openclaw/node_modules/jiti")(__filename);
const plugin = jiti("/data/projects/luke-agent-scripts/openclaw-plugins/ntm-quick/index.ts");

test.after(async () => {
  delete process.env.CLAWD_NTM_QUICK_STATE_FILE;
  delete process.env.NTM_QUICK_TIMEOUT_MS;
  delete process.env.NTM_QUICK_POLL_INTERVAL_MS;
  await fs.rm(tempRoot, { recursive: true, force: true });
});

function buildCtx(args) {
  return {
    args,
    commandBody: `/cmd ${args}`,
    channel: "test",
    channelId: "test",
    from: "test:sender",
    to: "test:chat",
    accountId: undefined,
    messageThreadId: undefined,
    senderId: "me",
    isAuthorizedSender: true,
    config: {},
  };
}

function tailPayload(lines) {
  return JSON.stringify({
    success: true,
    session: "test",
    panes: {
      "2": {
        type: "codex",
        state: "idle",
        lines,
      },
    },
  });
}

function withCtx(args, overrides = {}) {
  return {
    ...buildCtx(args),
    ...overrides,
  };
}

async function waitFor(predicate, timeoutMs = 250, intervalMs = 5) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    if (predicate()) return;
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  throw new Error("waitFor timeout");
}

function registerCommands(handler, options = {}) {
  const commands = new Map();
  const outgoing = [];
  const api = {
    runtime: {
      system: {
        runCommandWithTimeout: async (...args) => handler(...args),
      },
      channel: {
        telegram: {
          sendMessageTelegram: async (...args) => {
            outgoing.push({ provider: "telegram", args });
            return { messageId: "1", chatId: "chat" };
          },
        },
        discord: {
          sendMessageDiscord: async (...args) => {
            outgoing.push({ provider: "discord", args });
            return { messageId: "1", channelId: "channel" };
          },
        },
        slack: {
          sendMessageSlack: async (...args) => {
            outgoing.push({ provider: "slack", args });
            return { messageId: "1", channelId: "channel" };
          },
        },
        signal: {
          sendMessageSignal: async (...args) => {
            outgoing.push({ provider: "signal", args });
            return { timestamp: "1" };
          },
        },
        imessage: {
          sendMessageIMessage: async (...args) => {
            outgoing.push({ provider: "imessage", args });
            return { messageId: "1" };
          },
        },
        whatsapp: {
          sendMessageWhatsApp: async (...args) => {
            outgoing.push({ provider: "whatsapp", args });
            return { messageId: "1", toJid: "jid" };
          },
        },
        line: {
          sendMessageLine: async (...args) => {
            outgoing.push({ provider: "line", args });
            return { messageId: "1", chatId: "chat" };
          },
        },
      },
    },
    logger: {
      info: () => {},
      warn: () => {},
      error: () => {},
      ...(options.logger || {}),
    },
    registerCommand: (cmd) => {
      commands.set(cmd.name, cmd);
    },
  };

  plugin.default(api);
  return { commands, outgoing };
}

test("/nl runs ntm list and returns output", async () => {
  const seen = [];
  const { commands } = registerCommands(async (argv) => {
    if (argv[0] === "script") throw new Error("pty unavailable");
    seen.push(argv);
    return { stdout: "session-a\nsession-b\n", stderr: "", code: 0 };
  });

  const nl = commands.get("nl");
  const result = await nl.handler(buildCtx(""));

  assert.equal(result.text, "session-a\nsession-b");
  assert.deepEqual(seen.at(-1), ["ntm", "list"]);
});

test("/na saves project and /ns uses it for send+poll", async () => {
  const calls = [];
  let tailCalls = 0;

  const { commands } = registerCommands(async (argv) => {
    if (argv[0] === "script") throw new Error("pty unavailable");
    calls.push(argv);

    if (argv[1] && String(argv[1]).startsWith("--robot-send=")) {
      return { stdout: "", stderr: "", code: 0 };
    }

    if (argv[1] && String(argv[1]).startsWith("--robot-tail=")) {
      tailCalls += 1;
      if (tailCalls <= 2) {
        return {
          stdout: tailPayload(["› Hello world", "", "  ? for shortcuts   70% context left"]),
          stderr: "",
          code: 0,
        };
      }
      return {
        stdout: tailPayload(["› Hello world", "", "• Agent says hi"]),
        stderr: "",
        code: 0,
      };
    }

    return { stdout: "", stderr: "", code: 0 };
  });

  const na = commands.get("na");
  const ns = commands.get("ns");

  const saved = await na.handler(buildCtx("my-session"));
  assert.match(saved.text, /Saved ntm project: my-session/);

  const response = await ns.handler(buildCtx("Hello world"));
  assert.equal(response.text, "• Agent says hi");

  const sendCall = calls.find((call) => call[1] === "--robot-send=my-session");
  assert.ok(sendCall, "expected robot-send call");
  assert.ok(sendCall.includes("--track"), "expected --track in robot-send args");
  assert.equal(sendCall.at(-1), "--msg=Hello world\n\n");
});

test("/nc reads pane tail for saved project with default line count", async () => {
  const calls = [];
  const { commands } = registerCommands(async (argv) => {
    if (argv[0] === "script") throw new Error("pty unavailable");
    calls.push(argv);
    if (argv[1] && String(argv[1]).startsWith("--robot-tail=")) {
      return {
        stdout: tailPayload([
          "› command",
          "",
          "• response line",
          "",
          "────────────────────────────────────",
          "",
          "  ? for shortcuts   70% context left",
        ]),
        stderr: "",
        code: 0,
      };
    }
    return { stdout: "", stderr: "", code: 0 };
  });

  const na = commands.get("na");
  const nc = commands.get("nc");

  await na.handler(buildCtx("cat-session"));
  const result = await nc.handler(buildCtx(""));

  assert.equal(result.text, "› command\n• response line");
  const tailCall = calls.find((call) => call[1] === "--robot-tail=cat-session");
  assert.ok(tailCall, "expected robot-tail call");
  assert.ok(tailCall.includes("--lines=50"), "expected default /nc line count");
  assert.ok(tailCall.includes("--json"), "expected json mode");
});

test("/nc accepts custom line count", async () => {
  const calls = [];
  const { commands } = registerCommands(async (argv) => {
    if (argv[0] === "script") throw new Error("pty unavailable");
    calls.push(argv);
    if (argv[1] && String(argv[1]).startsWith("--robot-tail=")) {
      return { stdout: tailPayload(["› x", "• y"]), stderr: "", code: 0 };
    }
    return { stdout: "", stderr: "", code: 0 };
  });

  const na = commands.get("na");
  const nc = commands.get("nc");

  await na.handler(buildCtx("cat-lines"));
  await nc.handler(buildCtx("75"));

  const tailCall = calls.find((call) => call[1] === "--robot-tail=cat-lines");
  assert.ok(tailCall, "expected robot-tail call");
  assert.ok(tailCall.includes("--lines=75"), "expected custom /nc line count");
});

test("/nc returns usage for invalid line count", async () => {
  const { commands } = registerCommands(async () => ({ stdout: "", stderr: "", code: 0 }));
  const nc = commands.get("nc");

  let result = await nc.handler(buildCtx("abc"));
  assert.match(result.text, /Usage: \/nc \[lines\]/);

  result = await nc.handler(buildCtx("10 extra"));
  assert.match(result.text, /Usage: \/nc \[lines\]/);
});

test("/nc returns helpful error when no project saved", async () => {
  await fs.writeFile(process.env.CLAWD_NTM_QUICK_STATE_FILE, "{}\n", "utf8");

  const { commands } = registerCommands(async () => ({ stdout: "", stderr: "", code: 0 }));
  const nc = commands.get("nc");

  const result = await nc.handler(buildCtx(""));
  assert.match(result.text, /No ntm project saved/);
});

test("/ns returns helpful error when no project saved", async () => {
  await fs.writeFile(process.env.CLAWD_NTM_QUICK_STATE_FILE, "{}\n", "utf8");

  const { commands } = registerCommands(async () => ({ stdout: "", stderr: "", code: 0 }));
  const ns = commands.get("ns");

  const result = await ns.handler(buildCtx("hello"));
  assert.match(result.text, /No ntm project saved/);
});

test("/ns times out when no LLM response arrives", async () => {
  const { commands } = registerCommands(async (argv) => {
    if (argv[0] === "script") throw new Error("pty unavailable");
    if (argv[1] && String(argv[1]).startsWith("--robot-tail=")) {
      return {
        stdout: tailPayload(["› ping", "", "  ? for shortcuts   70% context left"]),
        stderr: "",
        code: 0,
      };
    }
    return { stdout: "", stderr: "", code: 0 };
  });

  const na = commands.get("na");
  const ns = commands.get("ns");

  await na.handler(buildCtx("session-timeout"));
  const result = await ns.handler(buildCtx("ping"));
  assert.match(result.text, /Timed out after 0s waiting for response/);
});

test("/nsa sends async result back to the same channel context", async () => {
  const calls = [];
  let tailCalls = 0;
  const { commands, outgoing } = registerCommands(async (argv) => {
    if (argv[0] === "script") throw new Error("pty unavailable");
    calls.push(argv);

    if (argv[1] && String(argv[1]).startsWith("--robot-send=")) {
      return { stdout: "", stderr: "", code: 0 };
    }
    if (argv[1] && String(argv[1]).startsWith("--robot-tail=")) {
      tailCalls += 1;
      if (tailCalls <= 2) {
        return {
          stdout: tailPayload(["› hello async", "", "  ? for shortcuts   70% context left"]),
          stderr: "",
          code: 0,
        };
      }
      return {
        stdout: tailPayload(["› hello async", "", "• Async reply payload"]),
        stderr: "",
        code: 0,
      };
    }
    return { stdout: "", stderr: "", code: 0 };
  });

  const na = commands.get("na");
  const nsa = commands.get("nsa");

  await na.handler(buildCtx("my-session-async"));
  const ack = await nsa.handler(
    withCtx("hello async", {
      channel: "telegram",
      channelId: "telegram",
      to: "telegram:-1001234567890",
      from: "telegram:12345",
      accountId: "acct-a",
      messageThreadId: 17,
    }),
  );
  assert.match(ack.text, /waiting for result/i);

  await waitFor(() => outgoing.length > 0, 400);
  assert.equal(outgoing[0].provider, "telegram");
  assert.equal(outgoing[0].args[0], "telegram:-1001234567890");
  assert.equal(outgoing[0].args[1], "• Async reply payload");
  assert.deepEqual(outgoing[0].args[2], { accountId: "acct-a", messageThreadId: 17 });

  const sendCall = calls.find((call) => call[1] === "--robot-send=my-session-async");
  assert.ok(sendCall, "expected robot-send call");
  assert.equal(sendCall.at(-1), "--msg=hello async\n\n");
});

test("/ns detects repeated response content when lines already exist in baseline", async () => {
  let tailCalls = 0;
  const repeatedQuestion = "› What's the current working directory?";
  const repeatedAnswer = "• /data/projects/misc";

  const { commands } = registerCommands(async (argv) => {
    if (argv[0] === "script") throw new Error("pty unavailable");
    if (argv[1] && String(argv[1]).startsWith("--robot-send=")) {
      return { stdout: "", stderr: "", code: 0 };
    }
    if (argv[1] && String(argv[1]).startsWith("--robot-tail=")) {
      tailCalls += 1;
      if (tailCalls === 1) {
        return {
          stdout: tailPayload([repeatedQuestion, "", repeatedAnswer]),
          stderr: "",
          code: 0,
        };
      }
      if (tailCalls === 2) {
        return {
          stdout: tailPayload([
            repeatedQuestion,
            "",
            repeatedAnswer,
            repeatedQuestion,
            "",
            repeatedAnswer,
          ]),
          stderr: "",
          code: 0,
        };
      }
      return {
        stdout: tailPayload([repeatedQuestion, "", repeatedAnswer]),
        stderr: "",
        code: 0,
      };
    }
    return { stdout: "", stderr: "", code: 0 };
  });

  const na = commands.get("na");
  const ns = commands.get("ns");

  await na.handler(buildCtx("repeat-session"));
  const result = await ns.handler(buildCtx("What's the current working directory?"));
  assert.equal(result.text, repeatedAnswer);
});

test("/ns ignores expanded baseline snapshots and returns only new response lines", async () => {
  let tailCalls = 0;
  const baselineLines = [
    "• old context line 1",
    "• old context line 2",
    "› status check",
    "• old status response",
  ];

  const { commands } = registerCommands(async (argv) => {
    if (argv[0] === "script") throw new Error("pty unavailable");
    if (argv[1] && String(argv[1]).startsWith("--robot-send=")) {
      return { stdout: "", stderr: "", code: 0 };
    }
    if (argv[1] && String(argv[1]).startsWith("--robot-tail=")) {
      tailCalls += 1;
      if (tailCalls === 1) {
        return { stdout: tailPayload(baselineLines), stderr: "", code: 0 };
      }
      return {
        stdout: tailPayload([
          "• older prefix line",
          "• another older prefix line",
          ...baselineLines,
          "› ping",
          "• fresh reply line",
        ]),
        stderr: "",
        code: 0,
      };
    }
    return { stdout: "", stderr: "", code: 0 };
  });

  const na = commands.get("na");
  const ns = commands.get("ns");
  await na.handler(buildCtx("expanded-session"));

  const result = await ns.handler(buildCtx("ping"));
  assert.equal(result.text, "• fresh reply line");
});

test("/ns ignores transient working lines and waits for final response", async () => {
  let tailCalls = 0;
  const { commands } = registerCommands(async (argv) => {
    if (argv[0] === "script") throw new Error("pty unavailable");
    if (argv[1] && String(argv[1]).startsWith("--robot-send=")) {
      return { stdout: "", stderr: "", code: 0 };
    }
    if (argv[1] && String(argv[1]).startsWith("--robot-tail=")) {
      tailCalls += 1;
      if (tailCalls === 1) {
        return {
          stdout: tailPayload(["› check status", "", "  ? for shortcuts   70% context left"]),
          stderr: "",
          code: 0,
        };
      }
      if (tailCalls === 2) {
        return {
          stdout: tailPayload(["› check status", "", "• Working (1s • esc to interrupt)"]),
          stderr: "",
          code: 0,
        };
      }
      return {
        stdout: tailPayload(["› check status", "", "• final completed response"]),
        stderr: "",
        code: 0,
      };
    }
    return { stdout: "", stderr: "", code: 0 };
  });

  const na = commands.get("na");
  const ns = commands.get("ns");
  await na.handler(buildCtx("working-session"));

  const result = await ns.handler(buildCtx("check status"));
  assert.equal(result.text, "• final completed response");
});
