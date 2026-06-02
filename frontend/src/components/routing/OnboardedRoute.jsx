import { useSelector } from 'react-redux'
import { Navigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'

export default function OnboardedRoute({ children }) {
  const { user, loading } = useSelector((s) => s.auth)

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-bg-primary">
        <Loader2 className="w-6 h-6 animate-spin text-emerald-600" />
      </div>
    )
  }

  if (!user) return <Navigate to="/" replace />

  if (!user.onboarding_complete) return <Navigate to="/onboarding" replace />

  return children
}
