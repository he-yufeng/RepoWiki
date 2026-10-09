import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import WikiView from "./pages/WikiView";
import ChatView from "./pages/ChatView";
import FileView from "./pages/FileView";
import MapView from "./pages/MapView";
import DiffView from "./pages/DiffView";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/project/:id" element={<WikiView />} />
        <Route path="/project/:id/chat" element={<ChatView />} />
        <Route path="/project/:id/file/*" element={<FileView />} />
        <Route path="/project/:id/map" element={<MapView />} />
        <Route path="/project/:id/diff" element={<DiffView />} />
      </Routes>
    </BrowserRouter>
  );
}
