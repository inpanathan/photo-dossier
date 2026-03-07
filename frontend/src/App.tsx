import { BrowserRouter, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import DossierPage from './pages/DossierPage';
import ResultsPage from './pages/ResultsPage';
import TimelinePage from './pages/TimelinePage';
import UploadPage from './pages/UploadPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<UploadPage />} />
          <Route path="/results" element={<ResultsPage />} />
          <Route path="/timeline" element={<TimelinePage />} />
          <Route path="/dossier" element={<DossierPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
