import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./App.css";
import LandingPage from "./pages/landing-page";
import MemoryPage from "./pages/memory-page";
import { Card } from "./components/memorypage/Card";
const mockCard = {
  cardId: "1",
  video_id: "sample.mp4",
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
          <Route path="/landing" element={<LandingPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}


export default App;
