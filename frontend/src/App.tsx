import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import WikiView from "./pages/WikiView";
import ChatView from "./pages/ChatView";
import FileView from "./pages/FileView";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/project/:id" element={<WikiView />} />
        <Route path="/project/:id/chat" element={<ChatView />} />
        <Route path="/project/:id/file/*" element={<FileView />} />
      </Routes>
    </BrowserRouter>
  );
}
