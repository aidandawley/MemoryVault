import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./App.css";
import LandingPage from "./pages/LandingPage";
import VaultCollectionPage from "./pages/VaultCollectionPage";
import VaultDetailPage from "./pages/VaultDetail";

function App() {
  return (
    <BrowserRouter>
      <div className="app-root">
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route
            path="/vaults"
            element={<VaultCollectionPage userName="Omar" />}
          />
          <Route path="/landing" element={<LandingPage />} />
          <Route path="/vaults/:vaultId" element={<VaultDetailPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
