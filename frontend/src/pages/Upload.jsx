import { useState } from 'react'
import { api } from '../services/api'

const SOURCE_TYPES = [
  { value: 'sap_fuel', label: 'SAP Fuel & Procurement', icon: '⛽', desc: 'ME2M export CSV (semicolon-delimited)' },
  { value: 'utility_electricity', label: 'Utility Electricity', icon: '⚡', desc: 'Portal CSV export (Green Button-style)' },
  { value: 'travel', label: 'Corporate Travel', icon: '✈️', desc: 'TMC travel report CSV (Concur-style)' },
]

export default function Upload() {
  const [sourceType, setSourceType] = useState('sap_fuel')
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [dragOver, setDragOver] = useState(false)

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    setError('')
    setResult(null)
    try {
      const data = await api.uploadFile(file, sourceType)
      setResult(data)
      setFile(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f) setFile(f)
  }

  return (
    <>
      <div className="page-header">
        <h2>Upload Data</h2>
        <p>Ingest emissions data from SAP, utility portals, or travel platforms</p>
      </div>
      <div className="page-body">
        {/* Source Type Selector */}
        <div className="card animate-in" style={{ marginBottom: '24px' }}>
          <h3 style={{ fontSize: '14px', fontWeight: 700, marginBottom: '16px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Select Data Source
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
            {SOURCE_TYPES.map(s => (
              <button
                key={s.value}
                onClick={() => setSourceType(s.value)}
                style={{
                  padding: '16px',
                  borderRadius: 'var(--radius-sm)',
                  border: `2px solid ${sourceType === s.value ? 'var(--emerald)' : 'var(--border-color)'}`,
                  background: sourceType === s.value ? 'var(--emerald-glow)' : 'var(--bg-glass)',
                  cursor: 'pointer',
                  textAlign: 'left',
                  fontFamily: 'var(--font)',
                  transition: 'var(--transition)',
                }}
              >
                <div style={{ fontSize: '24px', marginBottom: '8px' }}>{s.icon}</div>
                <div style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text-primary)' }}>{s.label}</div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>{s.desc}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Upload Zone */}
        <div className="card animate-in" style={{ marginBottom: '24px' }}>
          <div
            className={`upload-zone ${dragOver ? 'dragover' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
          >
            <input
              id="file-upload"
              type="file"
              accept=".csv,.txt,.tsv"
              onChange={(e) => setFile(e.target.files[0])}
            />
            <div className="icon">📁</div>
            <h3>{file ? file.name : 'Drop your CSV file here'}</h3>
            <p>{file ? `${(file.size / 1024).toFixed(1)} KB` : 'or click to browse — CSV, TSV, or TXT files up to 10MB'}</p>
          </div>

          {file && (
            <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button className="btn btn-secondary" onClick={() => setFile(null)}>Clear</button>
              <button id="upload-btn" className="btn btn-primary" onClick={handleUpload} disabled={uploading}>
                {uploading ? <><span className="loading-spinner" /> Processing...</> : '🚀 Upload & Process'}
              </button>
            </div>
          )}
        </div>

        {/* Error */}
        {error && <div className="error-message" style={{ marginBottom: '20px' }}>{error}</div>}

        {/* Result */}
        {result && (
          <div className="card animate-in">
            <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '16px' }}>
              {result.status === 'completed' ? '✅ Upload Successful' :
               result.status === 'completed_with_errors' ? '⚠️ Upload Completed with Errors' :
               '❌ Upload Failed'}
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
              <div>
                <div className="stat-label">Total Rows</div>
                <div style={{ fontSize: '24px', fontWeight: 700 }}>{result.row_count}</div>
              </div>
              <div>
                <div className="stat-label">Successful</div>
                <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--emerald)' }}>{result.success_count}</div>
              </div>
              <div>
                <div className="stat-label">Errors</div>
                <div style={{ fontSize: '24px', fontWeight: 700, color: result.error_count > 0 ? 'var(--red)' : 'var(--text-muted)' }}>{result.error_count}</div>
              </div>
            </div>
            {result.processing_log?.length > 0 && (
              <div style={{ marginTop: '16px' }}>
                <h4 style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '8px' }}>PROCESSING LOG</h4>
                <div className="raw-data-viewer">
                  {result.processing_log.map((log, i) => (
                    <div key={i}>Row {log.row}: {log.error}</div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </>
  )
}
