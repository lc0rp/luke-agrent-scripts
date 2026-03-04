const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const tempRoot = fsSync.mkdtempSync(path.join(os.tmpdir(), "run-plugin-test-"));
process.env.CLAWD_RUN_COMMANDS_FILE = path.join(tempRoot, "commands.md");

const jiti = require("/data/projects/openclaw/node_modules/jiti")(__filename);
const plugin = jiti("/home/ubuntu/clawd/.openclaw/extensions/run-command/index.ts");

test.after(async () => {
  delete process.env.CLAWD_RUN_COMMANDS_FILE;
  await fs.rm(tempRoot, { recursive: true, force: true });
});

function registerRunCommand() {
  let registered;
  const api = {
    registerCommand: (cmd) => {
      registered = cmd;
    },
  };

  plugin.default(api);
  return registered;
}

function buildCtx(args) {
  return {
    args,
    commandBody: `/run ${args}`,
    channel: "test",
    senderId: "me",
    isAuthorizedSender: true,
    config: {},
  };
}

test("registers /run command", () => {
  const run = registerRunCommand();
  assert.equal(run?.name, "run");
  assert.equal(run?.acceptsArgs, true);
  assert.equal(run?.requireAuth, true);
});

test("/run help is dynamic from options", async () => {
  const run = registerRunCommand();
  const result = await run.handler(buildCtx("help"));

  assert.match(result.text, /\/run help/);
  assert.match(result.text, /\/run \+q <label> <command>/);
  assert.match(result.text, /\/run -q <label>/);
  assert.match(result.text, /\/run q \[<label> \[args\.\.\.\]\]/);
  assert.match(result.text, /Placeholders: use \{1\}, \{2\}/);
});

test("quick command lifecycle: add, list, execute, update, delete", async () => {
  const run = registerRunCommand();

  let result = await run.handler(buildCtx("+q demo printf quick"));
  assert.match(result.text, /Saved quick command/);

  result = await run.handler(buildCtx("q"));
  assert.match(result.text, /`demo`/);
  assert.match(result.text, /printf quick/);

  result = await run.handler(buildCtx("q demo"));
  assert.match(result.text, /```/);
  assert.match(result.text, /quick/);

  result = await run.handler(buildCtx("+q demo printf updated"));
  assert.match(result.text, /Updated quick command/);

  result = await run.handler(buildCtx("q demo"));
  assert.match(result.text, /updated/);

  result = await run.handler(buildCtx("-q demo"));
  assert.match(result.text, /Deleted quick command/);

  result = await run.handler(buildCtx("q demo"));
  assert.match(result.text, /No quick command found/);
});

test("quick command templates substitute positional args", async () => {
  const run = registerRunCommand();

  let result = await run.handler(buildCtx('+q greet printf "%s %s" {1} {2}'));
  assert.match(result.text, /Saved quick command/);

  result = await run.handler(buildCtx("q greet hello world"));
  assert.match(result.text, /hello world/);
});

test("quick command templates require all positional args", async () => {
  const run = registerRunCommand();

  await run.handler(buildCtx('+q greet printf "%s %s" {1} {2}'));

  let result = await run.handler(buildCtx("q greet hello"));
  assert.match(result.text, /Missing required argument\(s\): \{2\}/);

  result = await run.handler(buildCtx("q greet hello world extra"));
  assert.match(result.text, /Too many positional arguments/);
});
