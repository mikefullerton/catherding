import { db } from "../db/client.js";
import { messageLog } from "../db/schema.js";
import { env } from "../config/env.js";

interface SendResult {
  status: "sent" | "failed";
  messageId?: string;
  error?: string;
}

export async function sendEmail(
  to: string,
  subject: string,
  body: string,
): Promise<SendResult> {
  if (!env.POSTMARK_API_KEY || !env.POSTMARK_FROM_EMAIL) {
    const [record] = await db
      .insert(messageLog)
      .values({
        channel: "email",
        recipientEmail: to,
        subject,
        body,
        status: "failed",
        error: "Email provider not configured",
      })
      .returning();
    return { status: "failed", error: "Email provider not configured" };
  }

  try {
    const res = await fetch("https://api.postmarkapp.com/email", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-Postmark-Server-Token": env.POSTMARK_API_KEY,
      },
      body: JSON.stringify({
        From: env.POSTMARK_FROM_EMAIL,
        To: to,
        Subject: subject,
        TextBody: body,
      }),
    });

    const data = (await res.json()) as { MessageID?: string; ErrorCode?: number; Message?: string };

    if (res.ok && data.MessageID) {
      const [record] = await db
        .insert(messageLog)
        .values({
          channel: "email",
          recipientEmail: to,
          subject,
          body,
          status: "sent",
          providerMessageId: data.MessageID,
          sentAt: new Date(),
        })
        .returning();
      return { status: "sent", messageId: data.MessageID };
    }

    const [record] = await db
      .insert(messageLog)
      .values({
        channel: "email",
        recipientEmail: to,
        subject,
        body,
        status: "failed",
        error: data.Message ?? "Unknown error",
      })
      .returning();
    return { status: "failed", error: data.Message ?? "Unknown error" };
  } catch (err) {
    const error = err instanceof Error ? err.message : "Unknown error";
    await db
      .insert(messageLog)
      .values({ channel: "email", recipientEmail: to, subject, body, status: "failed", error });
    return { status: "failed", error };
  }
}

export async function sendSms(to: string, body: string): Promise<SendResult> {
  if (!env.TWILIO_ACCOUNT_SID || !env.TWILIO_AUTH_TOKEN || !env.TWILIO_FROM_NUMBER) {
    await db
      .insert(messageLog)
      .values({ channel: "sms", recipientPhone: to, body, status: "failed", error: "SMS provider not configured" });
    return { status: "failed", error: "SMS provider not configured" };
  }

  try {
    const auth = btoa(`${env.TWILIO_ACCOUNT_SID}:${env.TWILIO_AUTH_TOKEN}`);
    const res = await fetch(
      `https://api.twilio.com/2010-04-01/Accounts/${env.TWILIO_ACCOUNT_SID}/Messages.json`,
      {
        method: "POST",
        headers: {
          Authorization: `Basic ${auth}`,
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: new URLSearchParams({
          To: to,
          From: env.TWILIO_FROM_NUMBER,
          Body: body,
        }),
      },
    );

    const data = (await res.json()) as { sid?: string; message?: string };

    if (res.ok && data.sid) {
      await db
        .insert(messageLog)
        .values({
          channel: "sms",
          recipientPhone: to,
          body,
          status: "sent",
          providerMessageId: data.sid,
          sentAt: new Date(),
        });
      return { status: "sent", messageId: data.sid };
    }

    await db
      .insert(messageLog)
      .values({ channel: "sms", recipientPhone: to, body, status: "failed", error: data.message ?? "Unknown error" });
    return { status: "failed", error: data.message ?? "Unknown error" };
  } catch (err) {
    const error = err instanceof Error ? err.message : "Unknown error";
    await db
      .insert(messageLog)
      .values({ channel: "sms", recipientPhone: to, body, status: "failed", error });
    return { status: "failed", error };
  }
}
