import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import WikiView from "./pages/WikiView";
import ChatView from "./pages/ChatView";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/project/:id" element={<WikiView />} />
        <Route path="/project/:id/chat" element={<ChatView />} />
      </Routes>
    </BrowserRouter>
  );
}
