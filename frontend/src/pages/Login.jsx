import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [isRegister, setIsRegister] = useState(false)
  const [email, setEmail] = useState('')
  const [tenantName, setTenantName] = useState('')
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      let data
      if (isRegister) {
        data = await api.register({ username, email, password, tenant_name: tenantName })
      } else {
        data = await api.login(username, password)
      }
      localStorage.setItem('access_token', data.access)
      localStorage.setItem('refresh_token', data.refresh)
      navigate('/')
    } catch (err) {
      setError(err.message || 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card animate-in">
        <h1>Breathe ESG</h1>
        <p className="subtitle">{isRegister ? 'Create your account' : 'Sign in to continue'}</p>

        {error && <div className="error-message">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Username</label>
            <input
              id="username"
              type="text"
              className="form-input"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              autoFocus
            />
          </div>

          {isRegister && (
            <>
              <div className="form-group">
                <label className="form-label">Email</label>
                <input id="email" type="email" className="form-input" value={email} onChange={e => setEmail(e.target.value)} required />
              </div>
              <div className="form-group">
                <label className="form-label">Organization Name</label>
                <input id="tenant" type="text" className="form-input" value={tenantName} onChange={e => setTenantName(e.target.value)} required />
              </div>
            </>
          )}

          <div className="form-group">
            <label className="form-label">Password</label>
            <input id="password" type="password" className="form-input" value={password} onChange={e => setPassword(e.target.value)} required />
          </div>

          <button id="login-btn" type="submit" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center', padding: '12px' }} disabled={loading}>
            {loading ? <span className="loading-spinner" /> : (isRegister ? 'Create Account' : 'Sign In')}
          </button>
        </form>

        <p style={{ textAlign: 'center', marginTop: '20px', fontSize: '13px', color: 'var(--text-muted)' }}>
          {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
          <button
            onClick={() => { setIsRegister(!isRegister); setError(''); }}
            style={{ background: 'none', border: 'none', color: 'var(--emerald)', cursor: 'pointer', fontFamily: 'var(--font)', fontSize: '13px', fontWeight: 600 }}
          >
            {isRegister ? 'Sign In' : 'Register'}
          </button>
        </p>
      </div>
    </div>
  )
}
