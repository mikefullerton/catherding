import { useState } from "react";
import { useAdminFlags, useCreateFlag, useToggleFlag, useDeleteFlag } from "../api/admin";

export function FlagsPage() {
  const { data, isLoading } = useAdminFlags();
  const createFlag = useCreateFlag();
  const toggleFlag = useToggleFlag();
  const deleteFlag = useDeleteFlag();

  const [newKey, setNewKey] = useState("");
  const [newDesc, setNewDesc] = useState("");

  function handleCreate() {
    if (!newKey) return;
    createFlag.mutate({ key: newKey, description: newDesc || undefined });
    setNewKey("");
    setNewDesc("");
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Feature Flags</h1>

      <div className="flex gap-2 mb-6">
        <input
          type="text"
          placeholder="Flag key (e.g. dark_mode)"
          value={newKey}
          onChange={(e) => setNewKey(e.target.value)}
          className="px-3 py-2 border rounded-lg flex-1"
        />
        <input
          type="text"
          placeholder="Description (optional)"
          value={newDesc}
          onChange={(e) => setNewDesc(e.target.value)}
          className="px-3 py-2 border rounded-lg flex-1"
        />
        <button onClick={handleCreate} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          Add Flag
        </button>
      </div>

      {isLoading ? (
        <p>Loading...</p>
      ) : (
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b text-left">
              <th className="py-2 px-3">Key</th>
              <th className="py-2 px-3">Description</th>
              <th className="py-2 px-3">Status</th>
              <th className="py-2 px-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {data?.flags.map((flag) => (
              <tr key={flag.id} className="border-b hover:bg-gray-50">
                <td className="py-2 px-3 font-mono text-sm">{flag.key}</td>
                <td className="py-2 px-3 text-sm text-gray-600">{flag.description ?? "—"}</td>
                <td className="py-2 px-3">
                  <button
                    onClick={() => toggleFlag.mutate({ key: flag.key, enabled: !flag.enabled })}
                    className={`px-3 py-1 rounded text-xs font-medium ${
                      flag.enabled
                        ? "bg-green-100 text-green-700 hover:bg-green-200"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                    }`}
                  >
                    {flag.enabled ? "Enabled" : "Disabled"}
                  </button>
                </td>
                <td className="py-2 px-3">
                  <button
                    onClick={() => { if (confirm(`Delete flag "${flag.key}"?`)) deleteFlag.mutate(flag.key); }}
                    className="text-red-600 text-sm hover:underline"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
