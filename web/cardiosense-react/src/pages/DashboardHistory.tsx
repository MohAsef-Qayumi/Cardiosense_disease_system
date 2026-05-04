import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

interface DayRecord {
  date: string;
  total: number;
  positive: number;
  negative: number;
  avgRisk: number;
  highConf: number;
  medConf: number;
  lowConf: number;
}

async function fetchDailyHistory(): Promise<DayRecord[]> {
  const res = await fetch(`${API_BASE}/analytics/summary?bucket=day`, {
    signal: AbortSignal.timeout(4000),
  });
  if (!res.ok) throw new Error("analytics fetch failed");
  const data = await res.json();
  const groups: any[] = data.groups || [];

  const dayMap: Record<string, DayRecord> = {};
  for (const g of groups) {
    if (!dayMap[g.date_bucket]) {
      dayMap[g.date_bucket] = {
        date: g.date_bucket,
        total: 0,
        positive: 0,
        negative: 0,
        avgRisk: 0,
        highConf: 0,
        medConf: 0,
        lowConf: 0,
      };
    }
    const d = dayMap[g.date_bucket];
    d.total += g.total_predictions;
    d.positive += g.positive_predictions;
    d.negative += g.negative_predictions;
    d.avgRisk += g.average_probability * g.total_predictions;
    if (g.confidence_tier === "HIGH") d.highConf += g.total_predictions;
    else if (g.confidence_tier === "MEDIUM") d.medConf += g.total_predictions;
    else d.lowConf += g.total_predictions;
  }

  return Object.values(dayMap)
    .map((d) => ({
      ...d,
      avgRisk: d.total > 0 ? (d.avgRisk / d.total) * 100 : 0,
    }))
    .sort((a, b) => b.date.localeCompare(a.date));
}

export default function DashboardHistory() {
  const [records, setRecords] = useState<DayRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const perPage = 7;

  useEffect(() => {
    fetchDailyHistory()
      .then(setRecords)
      .catch(() => setRecords([]))
      .finally(() => setLoading(false));
  }, []);

  const totalPages = Math.max(1, Math.ceil(records.length / perPage));
  const pageRecords = records.slice((page - 1) * perPage, page * perPage);

  return (
    <>
      <div className="dashboard-header" data-reveal>
        <h1>Prediction History</h1>
        <p>Daily prediction volume and outcomes from the backend.</p>
      </div>

      <div className="dashboard-panel" data-reveal>
        {loading ? (
          <div className="text-center py-5">
            <div className="spinner-border text-primary" role="status"></div>
            <p className="text-muted mt-3">Loading history...</p>
          </div>
        ) : records.length === 0 ? (
          <div className="text-center text-muted py-5">
            <i
              className="bi bi-inbox"
              style={{ fontSize: "3rem", opacity: 0.3 }}
            ></i>
            <p className="mt-3">
              No prediction history found. Make some predictions to see activity
              here.
            </p>
            <Link to="/dashboard/predict" className="btn btn-primary-cs mt-2">
              Make a Prediction
            </Link>
          </div>
        ) : (
          <>
            <div className="table-responsive">
              <table
                className="table table-hover"
                style={{ fontSize: "0.9rem" }}
              >
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Total</th>
                    <th>Positive</th>
                    <th>Negative</th>
                    <th>Avg Risk</th>
                    <th>Confidence Breakdown</th>
                  </tr>
                </thead>
                <tbody>
                  {pageRecords.map((rec) => (
                    <tr key={rec.date}>
                      <td>
                        <strong>{rec.date}</strong>
                      </td>
                      <td>{rec.total}</td>
                      <td>
                        <span
                          style={{ color: "var(--primary)", fontWeight: 600 }}
                        >
                          {rec.positive}
                        </span>
                      </td>
                      <td>
                        <span style={{ color: "var(--teal)", fontWeight: 600 }}>
                          {rec.negative}
                        </span>
                      </td>
                      <td>
                        <span
                          className={
                            rec.avgRisk > 60
                              ? "text-danger"
                              : rec.avgRisk > 35
                                ? "text-warning"
                                : "text-success"
                          }
                          style={{ fontWeight: 600 }}
                        >
                          {rec.avgRisk.toFixed(1)}%
                        </span>
                      </td>
                      <td>
                        <div
                          className="d-flex gap-2"
                          style={{ fontSize: "0.8rem" }}
                        >
                          {rec.highConf > 0 && (
                            <span
                              className="badge"
                              style={{
                                background: "#ede7f6",
                                color: "#7c4dff",
                              }}
                            >
                              H:{rec.highConf}
                            </span>
                          )}
                          {rec.medConf > 0 && (
                            <span
                              className="badge"
                              style={{
                                background: "#fff3e0",
                                color: "#ef6c00",
                              }}
                            >
                              M:{rec.medConf}
                            </span>
                          )}
                          {rec.lowConf > 0 && (
                            <span
                              className="badge"
                              style={{
                                background: "#e0f7f5",
                                color: "#00796b",
                              }}
                            >
                              L:{rec.lowConf}
                            </span>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <nav className="mt-4">
              <ul className="pagination justify-content-center">
                <li className={`page-item ${page === 1 ? "disabled" : ""}`}>
                  <button
                    className="page-link"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                  >
                    Previous
                  </button>
                </li>
                {Array.from({ length: totalPages }, (_, i) => i + 1).map(
                  (p) => (
                    <li
                      key={p}
                      className={`page-item ${p === page ? "active" : ""}`}
                    >
                      <button className="page-link" onClick={() => setPage(p)}>
                        {p}
                      </button>
                    </li>
                  ),
                )}
                <li
                  className={`page-item ${page === totalPages ? "disabled" : ""}`}
                >
                  <button
                    className="page-link"
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  >
                    Next
                  </button>
                </li>
              </ul>
            </nav>
          </>
        )}
      </div>
    </>
  );
}
