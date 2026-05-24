import { useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Upload from './pages/Upload'
import ReviewQueue from './pages/ReviewQueue'

function ProtectedRoute({ children }) {
  const token = localStorage.getItem('access_token')
  if (!token) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={
          <ProtectedRoute><Layout /></ProtectedRoute>
        }>
          <Route index element={<Dashboard />} />
          <Route path="upload" element={<Upload />} />
          <Route path="review" element={<ReviewQueue />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
