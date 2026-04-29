import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import ChatbotPage from './pages/ChatbotPage';
import ChartsPage from './pages/ChartsPage';
import SubsidiesPage from './pages/SubsidiesPage';

function PrivateRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-solar-yellow/30 border-t-solar-yellow rounded-full animate-spin" />
      </div>
    );
  }

  return isAuthenticated ? children : <Navigate to="/" replace />;
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/" element={<Login />} />
          <Route
            path="/dashboard"
            element={
              <PrivateRoute>
                <Dashboard />
              </PrivateRoute>
            }
          />
          <Route
            path="/chatbot"
            element={
              <PrivateRoute>
                <ChatbotPage />
              </PrivateRoute>
            }
          />
          <Route
            path="/graficas"
            element={
              <PrivateRoute>
                <ChartsPage />
              </PrivateRoute>
            }
          />
          <Route
            path="/subvenciones"
            element={
              <PrivateRoute>
                <SubsidiesPage />
              </PrivateRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
