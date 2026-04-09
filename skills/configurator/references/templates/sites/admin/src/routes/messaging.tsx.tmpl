import { useState, type FormEvent } from "react";
import { useMessageLog, useSendMessage } from "../api/admin";

export function MessagingPage() {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useMessageLog(page);
  const sendMessage = useSendMessage();

  const [channel, setChannel] = useState<"email" | "sms">("email");
  const [to, setTo] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");

  function handleSend(e: FormEvent) {
    e.preventDefault();
    sendMessage.mutate(
      { channel, to, ...(channel === "email" ? { subject } : {}), body },
      { onSuccess: () => { setTo(""); setSubject(""); setBody(""); } },
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Messaging</h1>

      <form onSubmit={handleSend} className="border rounded-lg p-4 mb-8 space-y-3">
        <h2 className="font-semibold">Send Message</h2>
        <div className="flex gap-2">
          <select value={channel} onChange={(e) => setChannel(e.target.value as "email" | "sms")} className="border rounded px-3 py-2">
            <option value="email">Email</option>
            <option value="sms">SMS</option>
          </select>
          <input
            type="text"
            placeholder={channel === "email" ? "recipient@example.com" : "+1234567890"}
            value={to}
            onChange={(e) => setTo(e.target.value)}
            required
            className="flex-1 px-3 py-2 border rounded-lg"
          />
        </div>
        {channel === "email" && (
          <input
            type="text"
            placeholder="Subject"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            required
            className="w-full px-3 py-2 border rounded-lg"
          />
        )}
        <textarea
          placeholder="Message body"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          required
          rows={3}
          className="w-full px-3 py-2 border rounded-lg"
        />
        <button type="submit" disabled={sendMessage.isPending} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
          {sendMessage.isPending ? "Sending..." : "Send"}
        </button>
      </form>

      <h2 className="font-semibold mb-3">Message Log</h2>
      {isLoading ? (
        <p>Loading...</p>
      ) : (
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b text-left">
              <th className="py-2 px-3">Channel</th>
              <th className="py-2 px-3">Recipient</th>
              <th className="py-2 px-3">Subject</th>
              <th className="py-2 px-3">Status</th>
              <th className="py-2 px-3">Sent</th>
            </tr>
          </thead>
          <tbody>
            {data?.messages.map((msg) => (
              <tr key={msg.id} className="border-b">
                <td className="py-2 px-3 text-sm">{msg.channel}</td>
                <td className="py-2 px-3 text-sm font-mono">{msg.recipientEmail ?? msg.recipientPhone}</td>
                <td className="py-2 px-3 text-sm">{msg.subject ?? "—"}</td>
                <td className="py-2 px-3">
                  <span className={`px-2 py-0.5 rounded text-xs ${
                    msg.status === "sent" ? "bg-green-100 text-green-700" : msg.status === "failed" ? "bg-red-100 text-red-700" : "bg-yellow-100 text-yellow-700"
                  }`}>
                    {msg.status}
                  </span>
                </td>
                <td className="py-2 px-3 text-sm text-gray-500">
                  {msg.sentAt ? new Date(msg.sentAt).toLocaleString() : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
