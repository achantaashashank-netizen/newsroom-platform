export interface Story {
  id: string;
  run_id: string;
  query: string;
  status: StoryStatus;
  confidence_tier?: "low" | "medium" | "high";
  overall_confidence?: number;
  fake_news_flags?: string[];
  headline?: string;
  sub_headline?: string;
  summary?: string;
  bullet_points?: string[];
  hashtags?: string[];
  caption_facebook?: string;
  caption_instagram?: string;
  selected_image_url?: string;
  candidate_images?: MediaAsset[];
  social_card_paths?: Record<"facebook" | "instagram", string>;
  seo_data?: SEOData;
  language: string;
  approval_status: ApprovalStatus;
  human_edits?: HumanEdit[];
  approved_at?: string;
  rejection_reason?: string;
  triggered_by: string;
  created_at: string;
  updated_at: string;
}

export type StoryStatus =
  | "discovering"
  | "verifying"
  | "summarizing"
  | "media"
  | "pending_approval"
  | "approved"
  | "rejected"
  | "publishing"
  | "published"
  | "failed";

export type ApprovalStatus = "pending" | "approved" | "rejected" | "editing";

export interface MediaAsset {
  url: string;
  local_path?: string;
  relevance_score: number;
  alt_text: string;
  source_attribution: string;
  is_ai_generated: boolean;
  width: number;
  height: number;
}

export interface SEOData {
  score: number;
  focus_keyword: string;
  secondary_keywords: string[];
  meta_description: string;
  slug: string;
  readability: string;
  tips: string[];
}

export interface HumanEdit {
  field: string;
  original: string;
  edited: string;
  editor_user_id: string;
  edited_at: string;
}
