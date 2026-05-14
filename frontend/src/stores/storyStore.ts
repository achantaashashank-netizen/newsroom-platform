import { create } from "zustand";
import { Story } from "@/types/story";

interface StoryStore {
  story: Story | null;
  isDirty: boolean;
  pendingApproval: {
    story_id: string;
    run_id: string;
    headline: string;
    confidence_tier?: string;
  } | null;
  setStory: (story: Story) => void;
  editField: (field: keyof Story, value: unknown) => void;
  applyUpdate: (patch: Partial<Story>) => void;
  setApprovalRequired: (payload: StoryStore["pendingApproval"]) => void;
  clearDirty: () => void;
  reset: () => void;
}

export const useStoryStore = create<StoryStore>((set) => ({
  story: null,
  isDirty: false,
  pendingApproval: null,

  setStory: (story) => set({ story, isDirty: false }),

  editField: (field, value) =>
    set((state) => ({
      story: state.story ? { ...state.story, [field]: value } : null,
      isDirty: true,
    })),

  applyUpdate: (patch) =>
    set((state) => ({
      story: state.story ? { ...state.story, ...patch } : null,
    })),

  setApprovalRequired: (payload) => set({ pendingApproval: payload }),

  clearDirty: () => set({ isDirty: false }),

  reset: () => set({ story: null, isDirty: false, pendingApproval: null }),
}));
