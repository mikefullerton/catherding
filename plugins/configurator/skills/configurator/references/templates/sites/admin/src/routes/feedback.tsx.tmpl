import { useState } from "react";
import { useFeedback, useUpdateFeedback } from "../api/admin";

export function FeedbackPage() {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const { data, isLoading } = useFeedback(page, statusFilter || undefined);
  const updateFeedback = useUpdateFeedback();

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Feedback</h1>

      <div className="mb-4">
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="border rounded px-3 py-2"
        >
          <option value="">All statuses</option>
          <option value="new">New</option>
          <option value="reviewed">Reviewed</option>
          <option value="resolved">Resolved</option>
          <option value="archived">Archived</option>
        </select>
      </div>

      {isLoading ? (
        <p>Loading...</p>
      ) : (
        <>
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b text-left">
                <th className="py-2 px-3">Category</th>
                <th className="py-2 px-3">Subject</th>
                <th className="py-2 px-3">Email</th>
                <th className="py-2 px-3">Status</th>
                <th className="py-2 px-3">Date</th>
                <th className="py-2 px-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {data?.feedback.map((fb) => (
                <tr key={fb.id} className="border-b hover:bg-gray-50">
                  <td className="py-2 px-3 text-sm">{fb.category}</td>
                  <td className="py-2 px-3 text-sm">{fb.subject ?? "—"}</td>
                  <td className="py-2 px-3 text-sm font-mono">{fb.email ?? "—"}</td>
                  <td className="py-2 px-3">
                    <select
                      value={fb.status}
                      onChange={(e) => updateFeedback.mutate({ id: fb.id, status: e.target.value })}
                      className="text-sm border rounded px-2 py-1"
                    >
                      <option value="new">new</option>
                      <option value="reviewed">reviewed</option>
                      <option value="resolved">resolved</option>
                      <option value="archived">archived</option>
                    </select>
                  </td>
                  <td className="py-2 px-3 text-sm text-gray-500">
                    {new Date(fb.createdAt).toLocaleDateString()}
                  </td>
                  <td className="py-2 px-3">
                    <button className="text-blue-600 text-sm hover:underline">View</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {data?.pagination && (
            <div className="flex gap-2 mt-4">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 border rounded disabled:opacity-50"
              >
                Prev
              </button>
              <span className="px-3 py-1 text-sm text-gray-600">
                Page {page} of {Math.ceil(data.pagination.total / data.pagination.limit)}
              </span>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={page * data.pagination.limit >= data.pagination.total}
                className="px-3 py-1 border rounded disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
