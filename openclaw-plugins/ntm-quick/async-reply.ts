import type { OpenClawPluginApi } from "openclaw/plugin-sdk";

export type CommandInvocationContext = {
  args?: string;
  channel?: string;
  channelId?: string;
  from?: string;
  to?: string;
  accountId?: string;
  messageThreadId?: number;
};

export type AsyncReplyOrigin = {
  channel: string;
  channelId?: string;
  from?: string;
  to?: string;
  accountId?: string;
  messageThreadId?: number;
};

export function resolveAsyncReplyOrigin(ctx: CommandInvocationContext): AsyncReplyOrigin {
  return {
    channel: (ctx.channel ?? "").trim().toLowerCase(),
    channelId: ctx.channelId?.trim().toLowerCase() || undefined,
    from: ctx.from?.trim() || undefined,
    to: ctx.to?.trim() || undefined,
    accountId: ctx.accountId?.trim() || undefined,
    messageThreadId: ctx.messageThreadId,
  };
}

export function resolveAsyncReplyTarget(origin: AsyncReplyOrigin): string | null {
  const to = origin.to?.trim();
  if (to && !to.startsWith("slash:")) {
    return to;
  }
  const from = origin.from?.trim();
  if (from) {
    return from;
  }
  return to || null;
}

export async function sendAsyncReply(
  api: OpenClawPluginApi,
  origin: AsyncReplyOrigin,
  text: string,
): Promise<void> {
  const channel = (origin.channelId || origin.channel || "").trim().toLowerCase();
  const target = resolveAsyncReplyTarget(origin);
  if (!target) {
    throw new Error("missing channel target");
  }

  if (channel === "telegram") {
    await api.runtime.channel.telegram.sendMessageTelegram(target, text, {
      accountId: origin.accountId,
      ...(typeof origin.messageThreadId === "number"
        ? { messageThreadId: origin.messageThreadId }
        : {}),
    });
    return;
  }

  if (channel === "discord") {
    await api.runtime.channel.discord.sendMessageDiscord(target, text, {
      accountId: origin.accountId,
    });
    return;
  }

  if (channel === "slack") {
    await api.runtime.channel.slack.sendMessageSlack(target, text, {
      accountId: origin.accountId,
    });
    return;
  }

  if (channel === "signal") {
    await api.runtime.channel.signal.sendMessageSignal(target, text, {
      accountId: origin.accountId,
    });
    return;
  }

  if (channel === "imessage") {
    await api.runtime.channel.imessage.sendMessageIMessage(target, text, {
      accountId: origin.accountId,
    });
    return;
  }

  if (channel === "whatsapp" || channel === "web") {
    await api.runtime.channel.whatsapp.sendMessageWhatsApp(target, text, {
      verbose: false,
      accountId: origin.accountId,
    });
    return;
  }

  if (channel === "line") {
    await api.runtime.channel.line.sendMessageLine(target, text, {
      accountId: origin.accountId,
    });
    return;
  }

  throw new Error(`unsupported channel: ${channel || "<unknown>"}`);
}

