import { Navigate, Route, Routes } from 'react-router-dom';

import { useAuth } from '../hooks/useAuth';
import AppLayout from '../components/AppLayout';
import LoginPage from '../pages/LoginPage';
import RegisterPage from '../pages/RegisterPage';
import OverviewPage from '../pages/OverviewPage';
import DatasetsPage from '../pages/DatasetsPage';
import ForecastsPage from '../pages/ForecastsPage';
import ForecastDetailsPage from '../pages/ForecastDetailsPage';
import ReportsPage from '../pages/ReportsPage';
import ReportDetailsPage from '../pages/ReportDetailsPage';
import NotFoundPage from '../pages/NotFoundPage';

const AppRoutes = () => {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<OverviewPage />} />
        <Route path="/datasets" element={<DatasetsPage />} />
        <Route path="/forecasts" element={<ForecastsPage />} />
        <Route path="/forecasts/:jobId" element={<ForecastDetailsPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/reports/:batchId" element={<ReportDetailsPage />} />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
};

export default AppRoutes;
