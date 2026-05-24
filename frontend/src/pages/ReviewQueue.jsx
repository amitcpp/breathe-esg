import { useState, useEffect, useCallback } from 'react'
import { api } from '../services/api'

const SCOPE_LABELS = { scope_1: 'Scope 1', scope_2: 'Scope 2', scope_3: 'Scope 3' }
const SCOPE_BADGE = { scope_1: 'badge-scope1', scope_2: 'badge-scope2', scope_3: 'badge-scope3' }
const STATUS_BADGE = { pending: 'badge-pending', approved: 'badge-approved', rejected: 'badge-rejected', flagged: 'badge-flagged' }

function formatCO2(kg) {
  if (kg == null) return '—'
  const n = parseFloat(kg)
  if (n >= 1000) return `${(n / 1000).toFixed(2)} t`
  return `${n.toFixed(1)} kg`
}

function formatDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString()
}

export default function ReviewQueue() {
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({ scope: '', review_status: '', ingestion__source_type: '', page: 1 })
  const [selected, setSelected] = useState(new Set())
  const [detailId, setDetailId] = useState(null)
  const [detail, setDetail] = useState(null)
  const [totalCount, setTotalCount] = useState(0)
  const [toast, setToast] = useState(null)
  const [actionNotes, setActionNotes] = useState('')

  const fetchRecords = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.getRecords(filters)
      setRecords(data.results || [])
      setTotalCount(data.count || 0)
    } catch (err) { console.error(err) }
    finally { setLoading(false) }
  }, [filters])

  useEffect(() => { fetchRecords() }, [fetchRecords])

  useEffect(() => {
    if (!detailId) { setDetail(null); return }
    api.getRecord(detailId).then(setDetail).catch(console.error)
  }, [detailId])

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3000)
  }

  const handleApprove = async () => {
    if (selected.size === 0) return
    try {
      await api.approveRecords([...selected], actionNotes)
      showToast(`${selected.size} records approved`)
      setSelected(new Set())
      setActionNotes('')
      fetchRecords()
    } catch (err) { showToast(err.message, 'error') }
  }

  const handleReject = async () => {
    if (selected.size === 0) return
    try {
      await api.rejectRecords([...selected], actionNotes)
      showToast(`${selected.size} records rejected`)
      setSelected(new Set())
      setActionNotes('')
      fetchRecords()
    } catch (err) { showToast(err.message, 'error') }
  }

  const handleLock = async () => {
    if (selected.size === 0) return
    try {
      await api.lockRecords([...selected])
      showToast(`${selected.size} records locked for audit`)
      setSelected(new Set())
      fetchRecords()
    } catch (err) { showToast(err.message, 'error') }
  }

  const toggleSelect = (id) => {
    const next = new Set(selected)
    next.has(id) ? next.delete(id) : next.add(id)
    setSelected(next)
  }

  const toggleAll = () => {
    if (selected.size === records.length) setSelected(new Set())
    else setSelected(new Set(records.map(r => r.id)))
  }

  const totalPages = Math.ceil(totalCount / 25)

  return (
    <>
      <div className="page-header">
        <h2>Review Queue</h2>
        <p>{totalCount} emission records — review, approve, and lock for audit</p>
      </div>
      <div className="page-body">
        {/* Filters */}
        <div className="filters-bar">
          <select id="filter-scope" className="form-select" value={filters.scope} onChange={e => setFilters(f => ({ ...f, scope: e.target.value, page: 1 }))}>
            <option value="">All Scopes</option>
            <option value="scope_1">Scope 1</option>
            <option value="scope_2">Scope 2</option>
            <option value="scope_3">Scope 3</option>
          </select>
          <select id="filter-status" className="form-select" value={filters.review_status} onChange={e => setFilters(f => ({ ...f, review_status: e.target.value, page: 1 }))}>
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="flagged">Flagged</option>
          </select>
          <select id="filter-source" className="form-select" value={filters.ingestion__source_type} onChange={e => setFilters(f => ({ ...f, ingestion__source_type: e.target.value, page: 1 }))}>
            <option value="">All Sources</option>
            <option value="sap_fuel">SAP Fuel</option>
            <option value="utility_electricity">Utility</option>
            <option value="travel">Travel</option>
          </select>
          <div style={{ flex: 1 }} />
          {selected.size > 0 && (
            <div className="btn-group">
              <input
                className="form-input"
                placeholder="Add notes..."
                value={actionNotes}
                onChange={e => setActionNotes(e.target.value)}
                style={{ width: '180px', padding: '6px 10px', fontSize: '12px' }}
              />
              <button id="btn-approve" className="btn btn-primary btn-sm" onClick={handleApprove}>✓ Approve ({selected.size})</button>
              <button id="btn-reject" className="btn btn-danger btn-sm" onClick={handleReject}>✕ Reject ({selected.size})</button>
              <button id="btn-lock" className="btn btn-secondary btn-sm" onClick={handleLock}>🔒 Lock ({selected.size})</button>
            </div>
          )}
        </div>

        {/* Data Table */}
        {loading ? (
          <div className="loading-overlay"><span className="loading-spinner" /> Loading records...</div>
        ) : records.length === 0 ? (
          <div className="empty-state">
            <div className="icon">📋</div>
            <h3>No records found</h3>
            <p>Upload some data or adjust your filters</p>
          </div>
        ) : (
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ width: '40px' }}>
                    <input type="checkbox" className="checkbox" checked={selected.size === records.length && records.length > 0} onChange={toggleAll} />
                  </th>
                  <th>Scope</th>
                  <th>Activity</th>
                  <th>Quantity</th>
                  <th>CO₂e</th>
                  <th>Period</th>
                  <th>Facility</th>
                  <th>Source</th>
                  <th>Status</th>
                  <th>Flags</th>
                </tr>
              </thead>
              <tbody>
                {records.map(r => (
                  <tr
                    key={r.id}
                    className={selected.has(r.id) ? 'row-selected' : ''}
                    style={{ cursor: 'pointer' }}
                    onClick={() => setDetailId(r.id)}
                  >
                    <td onClick={e => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        className="checkbox"
                        checked={selected.has(r.id)}
                        onChange={() => toggleSelect(r.id)}
                      />
                    </td>
                    <td><span className={`badge ${SCOPE_BADGE[r.scope] || ''}`}>{SCOPE_LABELS[r.scope]}</span></td>
                    <td style={{ fontWeight: 500 }}>{r.activity_type.replace(/_/g, ' ')}</td>
                    <td>{parseFloat(r.quantity).toLocaleString()} {r.unit}</td>
                    <td style={{ fontWeight: 600 }}>{formatCO2(r.co2e_kg)}</td>
                    <td style={{ fontSize: '12px' }}>{formatDate(r.period_start)}</td>
                    <td style={{ fontSize: '12px', maxWidth: '150px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {r.facility_name || r.facility_code || '—'}
                    </td>
                    <td style={{ fontSize: '12px' }}>{r.source_type === 'sap_fuel' ? '⛽' : r.source_type === 'utility_electricity' ? '⚡' : '✈️'}</td>
                    <td><span className={`badge ${STATUS_BADGE[r.review_status] || ''}`}>{r.review_status}</span></td>
                    <td>
                      {r.flag_count > 0 && (
                        <span className={`badge ${r.has_errors ? 'badge-error' : 'badge-warning'}`}>
                          {r.flag_count} {r.flag_count === 1 ? 'flag' : 'flags'}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="pagination">
            <button disabled={filters.page <= 1} onClick={() => setFilters(f => ({ ...f, page: f.page - 1 }))}>← Prev</button>
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => i + 1).map(p => (
              <button key={p} className={filters.page === p ? 'active' : ''} onClick={() => setFilters(f => ({ ...f, page: p }))}>{p}</button>
            ))}
            <button disabled={filters.page >= totalPages} onClick={() => setFilters(f => ({ ...f, page: f.page + 1 }))}>Next →</button>
          </div>
        )}
      </div>

      {/* Detail Panel */}
      {detailId && detail && (
        <div className="detail-panel">
          <div className="detail-header">
            <h3 style={{ fontSize: '16px', fontWeight: 700 }}>Record Detail</h3>
            <button className="btn btn-secondary btn-sm" onClick={() => setDetailId(null)}>✕ Close</button>
          </div>
          <div className="detail-body">
            {/* Overview */}
            <div className="detail-section">
              <h4>Overview</h4>
              <div className="detail-row"><span className="label">Scope</span><span className="value"><span className={`badge ${SCOPE_BADGE[detail.scope]}`}>{detail.scope_display}</span></span></div>
              <div className="detail-row"><span className="label">Activity</span><span className="value">{detail.activity_type.replace(/_/g, ' ')}</span></div>
              <div className="detail-row"><span className="label">Category</span><span className="value">{detail.scope_category.replace(/_/g, ' ')}</span></div>
              <div className="detail-row"><span className="label">CO₂e</span><span className="value" style={{ fontWeight: 700, fontSize: '16px' }}>{formatCO2(detail.co2e_kg)}</span></div>
            </div>

            {/* Activity Data */}
            <div className="detail-section">
              <h4>Activity Data</h4>
              <div className="detail-row"><span className="label">Normalized</span><span className="value">{parseFloat(detail.quantity).toLocaleString()} {detail.unit}</span></div>
              <div className="detail-row"><span className="label">Original</span><span className="value">{parseFloat(detail.original_quantity).toLocaleString()} {detail.original_unit}</span></div>
              <div className="detail-row"><span className="label">Period</span><span className="value">{formatDate(detail.period_start)} — {formatDate(detail.period_end)}</span></div>
              <div className="detail-row"><span className="label">Facility</span><span className="value">{detail.facility_name || detail.facility_code || '—'}</span></div>
            </div>

            {/* Emission Factor */}
            {detail.emission_factor_detail && (
              <div className="detail-section">
                <h4>Emission Factor</h4>
                <div className="detail-row"><span className="label">Source</span><span className="value">{detail.emission_factor_detail.source_db}</span></div>
                <div className="detail-row"><span className="label">Factor</span><span className="value">{detail.emission_factor_detail.co2e_per_unit} kgCO₂e/{detail.emission_factor_detail.unit}</span></div>
                {detail.emission_factor_detail.region && <div className="detail-row"><span className="label">Region</span><span className="value">{detail.emission_factor_detail.region}</span></div>}
              </div>
            )}

            {/* Flags */}
            {detail.flags?.length > 0 && (
              <div className="detail-section">
                <h4>Flags ({detail.flags.length})</h4>
                <div className="flag-list">
                  {detail.flags.map((f, i) => (
                    <div key={i} className={`flag-item ${f.severity}`}>
                      <span>{f.severity === 'error' ? '🔴' : f.severity === 'warning' ? '🟡' : '🔵'}</span>
                      <div>
                        <div style={{ fontWeight: 600 }}>{f.type.replace(/_/g, ' ')}</div>
                        <div style={{ opacity: 0.8 }}>{f.message}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Review Status */}
            <div className="detail-section">
              <h4>Review</h4>
              <div className="detail-row"><span className="label">Status</span><span className="value"><span className={`badge ${STATUS_BADGE[detail.review_status]}`}>{detail.review_status_display}</span></span></div>
              {detail.reviewed_by_name && <div className="detail-row"><span className="label">Reviewed by</span><span className="value">{detail.reviewed_by_name}</span></div>}
              {detail.reviewed_at && <div className="detail-row"><span className="label">Reviewed at</span><span className="value">{new Date(detail.reviewed_at).toLocaleString()}</span></div>}
              {detail.review_notes && <div className="detail-row"><span className="label">Notes</span><span className="value">{detail.review_notes}</span></div>}
              {detail.is_locked && <div className="detail-row"><span className="label">Locked</span><span className="value">🔒 {detail.locked_by_name} at {new Date(detail.locked_at).toLocaleString()}</span></div>}
            </div>

            {/* Raw Data */}
            {detail.raw_data && (
              <div className="detail-section">
                <h4>Raw Source Data</h4>
                <div className="raw-data-viewer">
                  {JSON.stringify(detail.raw_data, null, 2)}
                </div>
              </div>
            )}

            {/* Audit Trail */}
            {detail.audit_trail?.length > 0 && (
              <div className="detail-section">
                <h4>Audit Trail</h4>
                <div className="timeline">
                  {detail.audit_trail.map((log, i) => (
                    <div key={i} className="timeline-item">
                      <div className="action">{log.action_display}</div>
                      <div className="time">
                        {log.performed_by_name} • {new Date(log.performed_at).toLocaleString()}
                      </div>
                      {log.field_changed && (
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                          {log.field_changed}: {log.old_value} → {log.new_value}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && <div className={`toast toast-${toast.type}`}>{toast.msg}</div>}
    </>
  )
}
