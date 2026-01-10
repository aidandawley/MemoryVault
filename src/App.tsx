import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./App.css";
import LandingPage from "./pages/landing-page";
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
    <div className="app-root">
      {/* <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
        </Routes>
      </BrowserRouter> */}
      <div className="app-content">
        <Card card={mockCard} />
      </div>
    </div>
  );
}

export default App;
