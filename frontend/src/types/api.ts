export interface RedactionRequest {
  file: File;
  prompt?: string;
  preview_only?: boolean;
}

export interface RedactionResponse {
  job_id: string;
  success: boolean;
  message: string;
  preview_text?: string;
  entities_detected: number;
}

export interface JobStatusResponse {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  result?: {
    redacted_file_url?: string;
    preview_text?: string;
    entities_detected: number;
  };
  error?: string;
}

export interface SuggestionsRequest {
  text_sample: string;
}

export interface SuggestionsResponse {
  suggestions: string[];
  detected_entities: string[];
}

export interface UploadResponse {
  file_id: string;
  filename: string;
  size: number;
  content_type: string;
}

export interface ErrorResponse {
  detail: string;
  status_code: number;
}