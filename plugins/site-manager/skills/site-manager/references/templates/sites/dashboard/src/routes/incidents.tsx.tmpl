import { useQuery } from "@tanstack/react-query";

interface Incident {
  id: number;
  service: string;
  status: "investigating" | "identified" | "monitoring" | "resolved";
  title: string | null;
  description: string | null;
  started_at: string;
  resolved_at: string | null;
}

function useIncidents() {
  return useQuery<{ incidents: Incident[] }>({
    queryKey: ["dashboard", "incidents"],
    queryFn: () => fetch("/api/dashboard/incidents").then((r) => r.json()),
    refetchInterval: 60_000,
  });
}

const STATUS_STYLES = {
  investigating: "bg-red-100 text-red-700",
  identified: "bg-orange-100 text-orange-700",
  monitoring: "bg-yellow-100 text-yellow-700",
  resolved: "bg-green-100 text-green-700",
};

export function IncidentsPage() {
  const { data, isLoading } = useIncidents();

  const open = (data?.incidents ?? []).filter((i) => !i.resolved_at);
  const resolved = (data?.incidents ?? []).filter((i) => i.resolved_at);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Incidents</h1>

      {isLoading ? (
        <p>Loading...</p>
      ) : (
        <>
          {open.length > 0 && (
            <div className="mb-8">
              <h2 className="font-semibold text-red-600 mb-3">Active Incidents ({open.length})</h2>
              {open.map((incident) => (
                <div key={incident.id} className="p-4 border border-red-200 rounded-lg mb-2 bg-red-50">
                  <div className="flex items-center gap-2">
                    <span className="capitalize font-medium">{incident.service}</span>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_STYLES[incident.status]}`}>
                      {incident.status}
                    </span>
                  </div>
                  {incident.title && <p className="text-sm mt-1">{incident.title}</p>}
                  <p className="text-xs text-gray-500 mt-1">
                    Started: {new Date(incident.started_at).toLocaleString()}
                  </p>
                </div>
              ))}
            </div>
          )}

          {open.length === 0 && (
            <div className="p-6 bg-green-50 border border-green-200 rounded-lg mb-8 text-center">
              <p className="text-green-700 font-medium">All systems operational</p>
            </div>
          )}

          <h2 className="font-semibold mb-3">Resolved ({resolved.length})</h2>
          <div className="space-y-2">
            {resolved.map((incident) => (
              <div key={incident.id} className="p-3 border rounded-lg">
                <div className="flex items-center gap-2">
                  <span className="capitalize text-sm font-medium">{incident.service}</span>
                  <span className="px-2 py-0.5 rounded text-xs bg-green-100 text-green-700">resolved</span>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  {new Date(incident.started_at).toLocaleString()} — {new Date(incident.resolved_at!).toLocaleString()}
                </p>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
