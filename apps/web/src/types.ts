export interface DocumentSummary {
  id: number;
  title: string;
  created_at: string;
  status: string;
  audio_url: string | null;
}

export interface DocumentDetail {
  id: number;
  owner_id: number;
  title: string;
  text: string;
  created_at: string;
}
