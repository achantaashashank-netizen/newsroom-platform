import { create } from "zustand";
import { persist } from "zustand/middleware";

interface UIStore {
  activePreviewTab: "facebook" | "instagram";
  sidebarOpen: boolean;
  setActivePreviewTab: (tab: "facebook" | "instagram") => void;
  toggleSidebar: () => void;
}

export const useUIStore = create<UIStore>()(
  persist(
    (set) => ({
      activePreviewTab: "facebook",
      sidebarOpen: true,
      setActivePreviewTab: (tab) => set({ activePreviewTab: tab }),
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
    }),
    { name: "ui-store" }
  )
);
