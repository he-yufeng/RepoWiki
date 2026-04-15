import type { SidebarItem } from "../lib/api";

interface Props {
  sidebar: SidebarItem[];
  currentPageId: string;
  projectName: string;
  onNavigate: (pageId: string) => void;
  onChat: () => void;
  onHome: () => void;
}

export default function WikiSidebar({ sidebar, currentPageId, projectName, onNavigate, onChat, onHome }: Props) {
  return (
    <aside className="w-64 bg-slate-50 border-r border-slate-200 flex flex-col h-full shrink-0">
      <div className="px-4 py-4 border-b border-slate-200">
        <button onClick={onHome} className="text-lg font-bold text-slate-800 hover:text-blue-600 transition-colors">
          <span className="text-blue-600">Repo</span>Wiki
        </button>
        <p className="text-xs text-slate-500 mt-1 truncate">{projectName}</p>
      </div>

      <nav className="flex-1 overflow-y-auto py-2">
        {sidebar.map((item) => (
          <div key={item.page_id || item.title}>
            {item.page_id ? (
              <button
                onClick={() => onNavigate(item.page_id)}
                className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                  currentPageId === item.page_id
                    ? "bg-blue-50 text-blue-700 font-medium"
                    : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                {item.title}
              </button>
            ) : (
              <div className="px-4 pt-4 pb-1 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                {item.title}
              </div>
            )}
            {item.children?.map((child) => (
              <button
                key={child.page_id}
                onClick={() => onNavigate(child.page_id)}
                className={`w-full text-left pl-8 pr-4 py-1.5 text-sm transition-colors ${
                  currentPageId === child.page_id
                    ? "bg-blue-50 text-blue-700 font-medium"
                    : "text-slate-500 hover:bg-slate-100"
                }`}
              >
                {child.title}
              </button>
            ))}
          </div>
        ))}
      </nav>

      <div className="border-t border-slate-200 p-3">
        <button
          onClick={onChat}
          className="w-full px-3 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          Ask a Question
        </button>
      </div>
    </aside>
  );
}
