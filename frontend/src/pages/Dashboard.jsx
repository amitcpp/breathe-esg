import { useState, useEffect } from 'react'
import { api } from '../services/api'

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.dashboardSummary()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="loading-overlay"><span className="loading-spinner" /> Loading dashboard...</div>
  if (!data) return <div className="empty-state"><div className="icon">📊</div><h3>No data yet</h3><p>Upload some data to get started</p></div>

  const scopes = data.scope_totals || {}
  const s1 = scopes.scope_1?.co2e_kg || 0
  const s2 = scopes.scope_2?.co2e_kg || 0
  const s3 = scopes.scope_3?.co2e_kg || 0
  const maxScope = Math.max(s1, s2, s3, 1)
  const statusCounts = data.review_status_counts || {}

  const formatCO2 = (kg) => {
    if (kg >= 1000) return `${(kg / 1000).toFixed(2)} t`
    return `${kg.toFixed(1)} kg`
  }

  return (
    <>
      <div className="page-header">
        <h2>Dashboard</h2>
        <p>Emissions overview and review status</p>
      </div>
      <div className="page-body">
        {/* Summary Cards */}
        <div className="card-grid">
          <div className="card stat-card animate-in">
            <div className="stat-label">Total CO₂e</div>
            <div className="stat-value total">{formatCO2(data.total_co2e_kg)}</div>
            <div className="stat-sub">{data.total_records} records</div>
          </div>
          <div className="card stat-card animate-in">
            <div className="stat-label">Scope 1 — Direct</div>
            <div className="stat-value scope1">{formatCO2(s1)}</div>
            <div className="stat-sub">Fuel combustion • {scopes.scope_1?.count || 0} records</div>
          </div>
          <div className="card stat-card animate-in">
            <div className="stat-label">Scope 2 — Energy</div>
            <div className="stat-value scope2">{formatCO2(s2)}</div>
            <div className="stat-sub">Purchased electricity • {scopes.scope_2?.count || 0} records</div>
          </div>
          <div className="card stat-card animate-in">
            <div className="stat-label">Scope 3 — Travel</div>
            <div className="stat-value scope3">{formatCO2(s3)}</div>
            <div className="stat-sub">Business travel • {scopes.scope_3?.count || 0} records</div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          {/* Scope Breakdown */}
          <div className="card animate-in">
            <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '20px' }}>Emissions by Scope</h3>
            <div className="scope-bars">
              <div className="scope-bar-row">
                <div className="scope-bar-label" style={{ color: 'var(--red)' }}>Scope 1</div>
                <div className="scope-bar-track">
                  <div className="scope-bar-fill s1" style={{ width: `${(s1 / maxScope) * 100}%` }} />
                </div>
                <div className="scope-bar-value">{formatCO2(s1)}</div>
              </div>
              <div className="scope-bar-row">
                <div className="scope-bar-label" style={{ color: 'var(--amber)' }}>Scope 2</div>
                <div className="scope-bar-track">
                  <div className="scope-bar-fill s2" style={{ width: `${(s2 / maxScope) * 100}%` }} />
                </div>
                <div className="scope-bar-value">{formatCO2(s2)}</div>
              </div>
              <div className="scope-bar-row">
                <div className="scope-bar-label" style={{ color: 'var(--blue)' }}>Scope 3</div>
                <div className="scope-bar-track">
                  <div className="scope-bar-fill s3" style={{ width: `${(s3 / maxScope) * 100}%` }} />
                </div>
                <div className="scope-bar-value">{formatCO2(s3)}</div>
              </div>
            </div>
          </div>

          {/* Review Status */}
          <div className="card animate-in">
            <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '20px' }}>Review Status</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="badge badge-pending">⏳ Pending</span>
                <span style={{ fontSize: '20px', fontWeight: 700 }}>{statusCounts.pending || 0}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="badge badge-approved">✓ Approved</span>
                <span style={{ fontSize: '20px', fontWeight: 700 }}>{statusCounts.approved || 0}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="badge badge-rejected">✕ Rejected</span>
                <span style={{ fontSize: '20px', fontWeight: 700 }}>{statusCounts.rejected || 0}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="badge badge-flagged">⚠ Flagged</span>
                <span style={{ fontSize: '20px', fontWeight: 700 }}>{data.flagged_count || 0}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Uploads */}
        {data.recent_ingestions?.length > 0 && (
          <div className="card animate-in" style={{ marginTop: '20px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '16px' }}>Recent Uploads</h3>
            {data.recent_ingestions.map(ing => (
              <div key={ing.id} className="ingestion-card">
                <div className={`ingestion-icon ${ing.source_type === 'sap_fuel' ? 'sap' : ing.source_type === 'utility_electricity' ? 'utility' : 'travel'}`}>
                  {ing.source_type === 'sap_fuel' ? '⛽' : ing.source_type === 'utility_electricity' ? '⚡' : '✈️'}
                </div>
                <div className="ingestion-info">
                  <div className="name">{ing.file_name}</div>
                  <div className="meta">{ing.source_type_display} • {new Date(ing.uploaded_at).toLocaleString()}</div>
                </div>
                <div className="ingestion-stats">
                  <span className="success">✓ {ing.success_count}</span>
                  {ing.error_count > 0 && <span className="errors">✕ {ing.error_count}</span>}
                </div>
                <span className={`badge badge-${ing.status === 'completed' ? 'approved' : ing.status === 'failed' ? 'rejected' : 'pending'}`}>
                  {ing.status}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  )
}
