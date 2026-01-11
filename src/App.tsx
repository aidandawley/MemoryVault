/* eslint-disable @typescript-eslint/no-unused-vars */
import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./App.css";
import LandingPage from "./pages/landing-page";
import MemoryPage from "./pages/memory-page";
import { Card } from "./components/memorypage/Card";
import VaultCollectionPage from "./pages/vaults-collection";
const mockCard = {
  cardId: "1",
  media_id: "sample.mp4",
  media_type: "video",
  caption: "Testing UI",
  tags: ["tag1", "tag2"],
  isActive: true,
};

function App() {
  return (
    <BrowserRouter>
      <div className="app-root">
        <Routes>
          <Route path="/" element={<MemoryPage />} />
          <Route
            path="/vaults"
            element={<VaultCollectionPage userName="Omar" />}
          />
          <Route path="/landing" element={<LandingPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
