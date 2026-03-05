const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const tempRoot = fsSync.mkdtempSync(path.join(os.tmpdir(), "ntm-plugin-test-"));
process.env.CLAWD_RUN_COMMANDS_FILE = path.join(tempRoot, "commands.md");

const jiti = require("/data/projects/openclaw/node_modules/jiti")(__filename);
const plugin = jiti("/home/ubuntu/.openclaw/extensions/ntm/index.ts");

test.after(async () => {
  delete process.env.CLAWD_RUN_COMMANDS_FILE;
  await fs.rm(tempRoot, { recursive: true, force: true });
});

function registerNtmCommand() {
  let registered;
  const executed = [];

  const api = {
    runtime: {
      system: {
        runCommandWithTimeout: async (argv) => {
          if (Array.isArray(argv) && argv[0] === "script") {
            throw new Error("pty unavailable");
          }

          executed.push(argv);
          return {
            stdout: "mock-output\n",
            stderr: "",
            code: 0,
          };
        },
      },
    },
    registerCommand: (cmd) => {
      registered = cmd;
    },
  };

  plugin.default(api);
  return { command: registered, executed };
}

function buildCtx(args) {
  return {
    args,
    commandBody: `/ntm ${args}`,
    channel: "test",
    senderId: "me",
    isAuthorizedSender: true,
    config: {},
  };
}

test("/ntm help includes dynamic quick-command options", async () => {
  const { command: ntm } = registerNtmCommand();
  const result = await ntm.handler(buildCtx("help"));

  assert.match(result.text, /\/ntm help/);
  assert.match(result.text, /\/ntm \+q <label> <command>/);
  assert.match(result.text, /\/ntm -q <label>/);
  assert.match(result.text, /\/ntm q \[<label> \[args\.\.\.\]\]/);
  assert.match(result.text, /Placeholders: use \{1\}, \{2\}/);
});

test("/ntm quick command lifecycle", async () => {
  const { command: ntm } = registerNtmCommand();

  let result = await ntm.handler(buildCtx("+q demo list"));
  assert.match(result.text, /Saved quick command/);

  result = await ntm.handler(buildCtx("q"));
  assert.match(result.text, /`demo`/);
  assert.match(result.text, /ntm list/);

  result = await ntm.handler(buildCtx("q demo"));
  assert.match(result.text, /mock-output/);

  result = await ntm.handler(buildCtx("+q demo run -- echo hi"));
  assert.match(result.text, /Updated quick command/);

  result = await ntm.handler(buildCtx("-q demo"));
  assert.match(result.text, /Deleted quick command/);
});

test("/ntm quick command templates substitute positional args", async () => {
  const { command: ntm, executed } = registerNtmCommand();

  await ntm.handler(buildCtx("+q jump run {1} {2}"));
  await ntm.handler(buildCtx("q jump session cmd"));

  const last = executed.at(-1);
  assert.deepEqual(last, ["ntm", "run", "session", "cmd"]);
});

test("/ntm quick command templates require all positional args", async () => {
  const { command: ntm } = registerNtmCommand();

  await ntm.handler(buildCtx("+q jump run {1} {2}"));

  let result = await ntm.handler(buildCtx("q jump onlyone"));
  assert.match(result.text, /Missing required argument\(s\): \{2\}/);

  result = await ntm.handler(buildCtx("q jump a b c"));
  assert.match(result.text, /Too many positional arguments/);
});
