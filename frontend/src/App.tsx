import { Navigate, Route, Routes } from 'react-router-dom';
import { LoginPage } from './pages/Login';
import { AssetsPage } from './pages/Assets';
import { AssetDetailPage } from './pages/AssetDetail';
import { TransformationsPage } from './pages/Transformations';
import { LineagePage } from './pages/Lineage';
import { ImpactPage } from './pages/Impact';
import { RequireAuth } from './router/guards';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/assets"
        element={
          <RequireAuth>
            <AssetsPage />
          </RequireAuth>
        }
      />
      <Route
        path="/assets/:id"
        element={
          <RequireAuth>
            <AssetDetailPage />
          </RequireAuth>
        }
      />
      <Route
        path="/transformations"
        element={
          <RequireAuth>
            <TransformationsPage />
          </RequireAuth>
        }
      />
      <Route
        path="/lineage"
        element={
          <RequireAuth>
            <LineagePage />
          </RequireAuth>
        }
      />
      <Route
        path="/impact"
        element={
          <RequireAuth>
            <ImpactPage />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/assets" replace />} />
    </Routes>
  );
}
