import { useQuery } from "@tanstack/react-query";

interface Deployment {
  id: number;
  service: string;
  version: string | null;
  status: "deploying" | "deployed" | "failed" | "rolled_back";
  commit_sha: string | null;
  deployed_by: string | null;
  deployed_at: string;
}

function useDeployments() {
  return useQuery<{ deployments: Deployment[] }>({
    queryKey: ["dashboard", "deployments"],
    queryFn: () => fetch("/api/dashboard/deployments").then((r) => r.json()),
  });
}

const STATUS_STYLES = {
  deploying: "bg-blue-100 text-blue-700",
  deployed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
  rolled_back: "bg-orange-100 text-orange-700",
};

export function DeploymentsPage() {
  const { data, isLoading } = useDeployments();

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Deployments</h1>

      {isLoading ? (
        <p>Loading...</p>
      ) : (
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b text-left">
              <th className="py-2 px-3">Service</th>
              <th className="py-2 px-3">Version</th>
              <th className="py-2 px-3">Status</th>
              <th className="py-2 px-3">Commit</th>
              <th className="py-2 px-3">By</th>
              <th className="py-2 px-3">Deployed</th>
            </tr>
          </thead>
          <tbody>
            {(data?.deployments ?? []).map((deploy) => (
              <tr key={deploy.id} className="border-b hover:bg-gray-50">
                <td className="py-2 px-3 capitalize">{deploy.service}</td>
                <td className="py-2 px-3 font-mono text-sm">{deploy.version ?? "—"}</td>
                <td className="py-2 px-3">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_STYLES[deploy.status]}`}>
                    {deploy.status}
                  </span>
                </td>
                <td className="py-2 px-3 font-mono text-xs">{deploy.commit_sha?.slice(0, 7) ?? "—"}</td>
                <td className="py-2 px-3 text-sm">{deploy.deployed_by ?? "—"}</td>
                <td className="py-2 px-3 text-sm text-gray-500">
                  {new Date(deploy.deployed_at).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
