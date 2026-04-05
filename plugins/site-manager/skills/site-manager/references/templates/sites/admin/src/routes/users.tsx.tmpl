import { useAdminUsers } from "../api/admin";

export function UsersPage() {
  const { data, isLoading } = useAdminUsers(1);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6" style={{ color: "#e8e6e3" }}>Users</h1>

      {isLoading ? (
        <p style={{ color: "#8a8a9a" }}>Loading...</p>
      ) : (
        <div className="overflow-x-auto rounded-lg" style={{ border: "1px solid #2a2a36" }}>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase" style={{ background: "#14141a", color: "#5a5a6a" }}>
                <th className="px-4 py-3">User</th>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Role</th>
                <th className="px-4 py-3">Joined</th>
              </tr>
            </thead>
            <tbody>
              {data?.users.map((user) => (
                <tr
                  key={user.id}
                  style={{ borderBottom: "1px solid #2a2a36" }}
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div
                        className="flex h-8 w-8 items-center justify-center rounded-full text-xs font-medium"
                        style={{ background: "#2a2a36", color: "#8a8a9a" }}
                      >
                        {(user.displayName ?? user.email).charAt(0).toUpperCase()}
                      </div>
                      <span className="font-medium" style={{ color: "#e8e6e3" }}>
                        {user.displayName ?? "—"}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3" style={{ color: "#8a8a9a", fontFamily: "'DM Mono', monospace", fontSize: "13px" }}>
                    {user.email}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className="inline-flex rounded-full px-2 py-0.5 text-xs font-medium"
                      style={
                        user.role === "admin"
                          ? { background: "rgba(212, 84, 84, 0.15)", color: "#d45454", border: "1px solid rgba(212, 84, 84, 0.3)" }
                          : { background: "rgba(138, 138, 154, 0.1)", color: "#8a8a9a", border: "1px solid rgba(138, 138, 154, 0.2)" }
                      }
                    >
                      {user.role}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs" style={{ color: "#5a5a6a" }}>
                    {new Date(user.createdAt).toLocaleDateString()}
                  </td>
                </tr>
              ))}
              {(!data?.users || data.users.length === 0) && (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center" style={{ color: "#5a5a6a" }}>
                    No users found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
