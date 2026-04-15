import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getWiki, getPage } from "../lib/api";
import { useWikiStore } from "../stores/wiki";
import WikiSidebar from "../components/WikiSidebar";
import WikiContent from "../components/WikiContent";

export default function WikiView() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { wiki, setWiki, currentPageId, setCurrentPage } = useWikiStore();
  const [pageContent, setPageContent] = useState("");
  const [pageTitle, setPageTitle] = useState("");
  const [loading, setLoading] = useState(false);

  // load wiki structure if not already loaded
  useEffect(() => {
    if (!wiki && id) {
      getWiki(id).then((w) => {
        if ("error" in w) {
          navigate("/");
          return;
        }
        setWiki(w);
      });
    }
  }, [id, wiki]);

  // load page content when currentPageId changes
  useEffect(() => {
    if (!id || !currentPageId) return;
    setLoading(true);
    getPage(id, currentPageId).then((p) => {
      if ("error" in p) {
        setPageContent("Page not found");
        setPageTitle("Error");
      } else {
        setPageContent(p.content);
        setPageTitle(p.title);
      }
      setLoading(false);
    });
  }, [id, currentPageId]);

  if (!wiki) {
    return (
      <div className="min-h-screen flex items-center justify-center text-slate-500">
        Loading wiki...
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-white">
      {/* sidebar */}
      <WikiSidebar
        sidebar={wiki.sidebar}
        currentPageId={currentPageId}
        projectName={wiki.project_name}
        onNavigate={(pageId) => setCurrentPage(pageId)}
        onChat={() => navigate(`/project/${id}/chat`)}
        onHome={() => navigate("/")}
      />

      {/* main content */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="p-12 text-slate-400 animate-pulse">Loading page...</div>
        ) : (
          <WikiContent content={pageContent} title={pageTitle} />
        )}
      </div>
    </div>
  );
}
