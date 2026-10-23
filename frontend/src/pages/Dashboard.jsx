import { useCallback, useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  clearHistory,
  clearUnanswered,
  deleteUnanswered,
  fetchHistory,
  fetchMetrics,
  fetchUnanswered,
  runBatchEval,
  updateUnanswered,
} from '../api.js'

const TREND_COLORS = { relevance: '#38bdf8', faithfulness: '#a78bfa', overall: '#34d399' }
const ROUTE_COLORS = { RAG: '#38bdf8', Direct: '#f59e0b' }
const VERDICT_COLORS = { PASS: '#34d399', FAIL: '#f87171' }

function fmtPct(v) {
  return v == null ? '—' : `${Math.round(v * 100)}%`
}

function fmtTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

function KpiCard({ label, value, accent }) {
  return (
    <div className={`kpi-card ${accent || ''}`}>
      <span className="kpi-value">{value}</span>
      <span className="kpi-label">{label}</span>
    </div>
  )
}

function ChartCard({ title, children }) {
  return (
    <div className="chart-card">
      <h3>{title}</h3>
      <div className="chart-body">{children}</div>
    </div>
  )
}

export default function Dashboard() {
  const [metrics, setMetrics] = useState(null)
  const [history, setHistory] = useState([])
  const [unanswered, setUnanswered] = useState([])
  const [unansweredSummary, setUnansweredSummary] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [batchRunning, setBatchRunning] = useState(false)

  const refresh = useCallback(async () => {
    try {
      const [m, h, u] = await Promise.all([fetchMetrics(), fetchHistory(50), fetchUnanswered(100)])
      setMetrics(m)
      setHistory(h.records)
      setUnanswered(u.records)
      setUnansweredSummary(u.summary)
      setError(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, 15000)
    return () => clearInterval(id)
  }, [refresh])

  async function handleBatch() {
    setBatchRunning(true)
    setError(null)
    try {
      await runBatchEval([])
      await refresh()
    } catch (e) {
      setError(e.message)
    } finally {
      setBatchRunning(false)
    }
  }

  async function handleClear() {
    if (!window.confirm('Clear all evaluation history?')) return
    try {
      await clearHistory()
      await refresh()
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleStatus(id, status) {
    try {
      await updateUnanswered(id, status)
      await refresh()
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleDeleteUnanswered(id) {
    try {
      await deleteUnanswered(id)
      await refresh()
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleClearUnanswered() {
    if (!window.confirm('Clear all unanswered queries from the database?')) return
    try {
      await clearUnanswered()
      await refresh()
    } catch (e) {
      setError(e.message)
    }
  }

  if (loading && !metrics) {
    return <div className="dashboard loading-page">Loading metrics…</div>
  }

  const trendData = (metrics?.score_trend || []).map((t, i) => ({
    index: i + 1,
    Relevance: t.relevance != null ? +(t.relevance * 100).toFixed(1) : null,
    Faithfulness: t.faithfulness != null ? +(t.faithfulness * 100).toFixed(1) : null,
    Overall: t.overall != null ? +(t.overall * 100).toFixed(1) : null,
  }))

  const routeData = [
    { name: 'RAG (Policy)', value: metrics?.rag_queries || 0 },
    { name: 'Direct LLM', value: metrics?.direct_queries || 0 },
  ].filter((d) => d.value > 0)

  const verdictData = [
    { name: 'PASS', value: metrics?.pass_count || 0 },
    { name: 'FAIL', value: metrics?.fail_count || 0 },
  ].filter((d) => d.value > 0)

  const comparisonData = metrics
    ? [
        { metric: 'Relevance', RAG: pctOrNull(metrics.route_comparison.relevance.rag), Direct: pctOrNull(metrics.route_comparison.relevance.direct) },
        { metric: 'Faithfulness', RAG: pctOrNull(metrics.route_comparison.faithfulness.rag), Direct: pctOrNull(metrics.route_comparison.faithfulness.direct) },
        { metric: 'Overall', RAG: pctOrNull(metrics.route_comparison.overall.rag), Direct: pctOrNull(metrics.route_comparison.overall.direct) },
      ]
    : []

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div>
          <h2>RAG Evaluation Dashboard</h2>
          <p>LLM-as-judge scores (relevance · faithfulness · overall) across all conversations</p>
        </div>
        <div className="dashboard-actions">
          <button className="secondary" onClick={refresh} disabled={loading}>
            Refresh
          </button>
          <button className="primary" onClick={handleBatch} disabled={batchRunning}>
            {batchRunning ? 'Running batch eval…' : 'Run Batch Evaluation'}
          </button>
          <button className="danger" onClick={handleClear}>
            Clear History
          </button>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}
      {batchRunning && (
        <div className="info-banner">
          Running 10 standard HR questions through the full agent pipeline (route → generate →
          evaluate). This can take a couple of minutes…
        </div>
      )}

      <div className="kpi-grid">
        <KpiCard label="Total Queries" value={metrics?.total_queries ?? 0} />
        <KpiCard label="Pass Rate" value={fmtPct(metrics?.pass_rate)} accent="good" />
        <KpiCard label="Avg Overall" value={fmtPct(metrics?.avg_overall)} />
        <KpiCard label="Avg Relevance" value={fmtPct(metrics?.avg_relevance)} />
        <KpiCard label="Avg Faithfulness" value={fmtPct(metrics?.avg_faithfulness)} />
        <KpiCard
          label="RAG / Direct"
          value={`${metrics?.rag_queries ?? 0} / ${metrics?.direct_queries ?? 0}`}
        />
        <KpiCard
          label="Unanswered (Open)"
          value={`${unansweredSummary?.open ?? 0} / ${unansweredSummary?.total ?? 0}`}
          accent={(unansweredSummary?.total ?? 0) > 0 ? 'warn' : ''}
        />
      </div>

      <div className="charts-grid">
        <ChartCard title="Score Trend (per evaluation, chronological)">
          {trendData.length === 0 ? (
            <p className="chart-empty">No scored evaluations yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                <XAxis dataKey="index" stroke="#94a3b8" label={{ value: 'Eval #', position: 'insideBottomRight', offset: -2 }} />
                <YAxis domain={[0, 100]} stroke="#94a3b8" />
                <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155' }} />
                <Legend />
                <Line type="monotone" dataKey="Relevance" stroke={TREND_COLORS.relevance} dot={false} connectNulls strokeWidth={2} />
                <Line type="monotone" dataKey="Faithfulness" stroke={TREND_COLORS.faithfulness} dot={false} connectNulls strokeWidth={2} />
                <Line type="monotone" dataKey="Overall" stroke={TREND_COLORS.overall} dot={false} connectNulls strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        <ChartCard title="Routing Distribution">
          {routeData.length === 0 ? (
            <p className="chart-empty">No queries yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={routeData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90} label>
                  <Cell fill={ROUTE_COLORS.RAG} />
                  <Cell fill={ROUTE_COLORS.Direct} />
                </Pie>
                <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155' }} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        <ChartCard title="Verdicts (PASS ≥ 0.7 overall)">
          {verdictData.length === 0 ? (
            <p className="chart-empty">No evaluations yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={verdictData} dataKey="value" nameKey="name" outerRadius={90} label>
                  <Cell fill={VERDICT_COLORS.PASS} />
                  <Cell fill={VERDICT_COLORS.FAIL} />
                </Pie>
                <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155' }} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        <ChartCard title="Avg Score: RAG vs Direct (%)">
          {!comparisonData.some((d) => d.RAG != null || d.Direct != null) ? (
            <p className="chart-empty">No scored evaluations yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={comparisonData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                <XAxis dataKey="metric" stroke="#94a3b8" />
                <YAxis domain={[0, 100]} stroke="#94a3b8" />
                <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155' }} />
                <Legend />
                <Bar dataKey="RAG" fill={ROUTE_COLORS.RAG} radius={[4, 4, 0, 0]} />
                <Bar dataKey="Direct" fill={ROUTE_COLORS.Direct} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
      </div>

      <div className="history-card unanswered-card">
        <div className="card-head">
          <div>
            <h3>Unanswered Queries (Knowledge Base Gaps)</h3>
            <p className="card-sub">
              Permanently stored in SQLite for HR follow-up. {unansweredSummary?.open ?? 0} open ·{' '}
              {unansweredSummary?.resolved ?? 0} resolved · {unansweredSummary?.total ?? 0} total
            </p>
          </div>
          <button className="danger" onClick={handleClearUnanswered} disabled={unanswered.length === 0}>
            Clear All
          </button>
        </div>
        {unanswered.length === 0 ? (
          <p className="chart-empty">
            No unanswered queries. Every question has been grounded in the HR policies.
          </p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Query</th>
                  <th>Route</th>
                  <th>Reason</th>
                  <th>Source</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {unanswered.map((r) => (
                  <tr key={r.id}>
                    <td className="nowrap">{fmtTime(r.timestamp)}</td>
                    <td className="query-cell" title={r.query}>{r.query}</td>
                    <td>
                      <span className={`badge ${r.used_rag ? 'rag' : 'direct'}`}>
                        {r.used_rag ? 'RAG' : 'Direct'}
                      </span>
                    </td>
                    <td className="nowrap">{r.reason || '—'}</td>
                    <td>{r.source}</td>
                    <td>
                      <span className={`status-pill ${r.status}`}>{r.status}</span>
                    </td>
                    <td className="actions-cell">
                      {r.status !== 'resolved' && (
                        <button
                          className="mini"
                          onClick={() => handleStatus(r.id, 'resolved')}
                          title="Mark resolved"
                        >
                          Resolve
                        </button>
                      )}
                      {r.status === 'open' && (
                        <button
                          className="mini secondary"
                          onClick={() => handleStatus(r.id, 'reviewing')}
                          title="Mark as in review"
                        >
                          Review
                        </button>
                      )}
                      {r.status === 'reviewing' && (
                        <button
                          className="mini secondary"
                          onClick={() => handleStatus(r.id, 'open')}
                          title="Reopen"
                        >
                          Reopen
                        </button>
                      )}
                      <button
                        className="mini danger"
                        onClick={() => handleDeleteUnanswered(r.id)}
                        title="Delete"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="history-card">
        <h3>Recent Evaluations</h3>
        {history.length === 0 ? (
          <p className="chart-empty">No history yet. Chat with the bot or run a batch evaluation.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Query</th>
                  <th>Route</th>
                  <th>Source</th>
                  <th>Relevance</th>
                  <th>Faithfulness</th>
                  <th>Overall</th>
                  <th>Verdict</th>
                </tr>
              </thead>
              <tbody>
                {history.map((r) => {
                  const ev = r.evaluation || {}
                  const hasErr = ev.error != null
                  return (
                    <tr key={r.id}>
                      <td className="nowrap">{fmtTime(r.timestamp)}</td>
                      <td className="query-cell" title={r.query}>{r.query}</td>
                      <td>
                        <span className={`badge ${r.used_rag ? 'rag' : 'direct'}`}>
                          {r.used_rag ? 'RAG' : 'Direct'}
                        </span>
                      </td>
                      <td>{r.source}</td>
                      <td>{hasErr ? '—' : fmtPct(ev.relevance_score)}</td>
                      <td>{hasErr ? '—' : fmtPct(ev.faithfulness_score)}</td>
                      <td>{hasErr ? '—' : fmtPct(ev.overall_score)}</td>
                      <td>
                        {hasErr ? (
                          <span className="badge fail">ERROR</span>
                        ) : (
                          <span className={`verdict ${ev.verdict === 'PASS' ? 'pass' : 'fail'}`}>
                            {ev.verdict}
                          </span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

function pctOrNull(v) {
  return v == null ? null : +(v * 100).toFixed(1)
}
