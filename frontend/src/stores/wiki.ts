import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { ProjectInfo, WikiStructure, SidebarItem } from "../lib/api";

interface WikiStore {
  projectId: string;
  project: ProjectInfo | null;
  wiki: WikiStructure | null;
  currentPageId: string;
  scanProgress: string[];
  chatMessages: { role: string; content: string }[];
  loading: boolean;
  error: string;
  settings: { apiKey: string; model: string; language: string };

  setProjectId: (id: string) => void;
  setProject: (p: ProjectInfo) => void;
  setWiki: (w: WikiStructure) => void;
  setCurrentPage: (id: string) => void;
  addProgress: (step: string) => void;
  addChatMessage: (msg: { role: string; content: string }) => void;
  appendToLastChat: (text: string) => void;
  setLoading: (v: boolean) => void;
  setError: (e: string) => void;
  updateSettings: (s: Partial<WikiStore["settings"]>) => void;
  reset: () => void;
}

export const useWikiStore = create<WikiStore>()(
  persist(
    (set) => ({
      projectId: "",
      project: null,
      wiki: null,
      currentPageId: "index",
      scanProgress: [],
      chatMessages: [],
      loading: false,
      error: "",
      settings: { apiKey: "", model: "deepseek", language: "en" },

      setProjectId: (id) => set({ projectId: id }),
      setProject: (p) => set({ project: p }),
      setWiki: (w) => set({ wiki: w }),
      setCurrentPage: (id) => set({ currentPageId: id }),
      addProgress: (step) =>
        set((s) => ({ scanProgress: [...s.scanProgress, step] })),
      addChatMessage: (msg) =>
        set((s) => ({ chatMessages: [...s.chatMessages, msg] })),
      appendToLastChat: (text) =>
        set((s) => {
          const msgs = [...s.chatMessages];
          if (msgs.length > 0 && msgs[msgs.length - 1].role === "assistant") {
            msgs[msgs.length - 1] = {
              ...msgs[msgs.length - 1],
              content: msgs[msgs.length - 1].content + text,
            };
          }
          return { chatMessages: msgs };
        }),
      setLoading: (v) => set({ loading: v }),
      setError: (e) => set({ error: e }),
      updateSettings: (s) =>
        set((state) => ({ settings: { ...state.settings, ...s } })),
      reset: () =>
        set({
          projectId: "",
          project: null,
          wiki: null,
          currentPageId: "index",
          scanProgress: [],
          chatMessages: [],
          loading: false,
          error: "",
        }),
    }),
    {
      name: "repowiki-store",
      storage: createJSONStorage(() => sessionStorage),
      partialize: (state) => ({
        projectId: state.projectId,
        settings: state.settings,
      }),
    },
  ),
);
