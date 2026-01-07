export type ExportFormat = 'markdown' | 'html' | 'text';

export interface ExportRequest {
  session_id: number;
  format: ExportFormat;
  report_title: string;
}

export interface ExportRecord {
  id: number;
  user_id: number;
  session_id: number;
  report_title: string;
  format: ExportFormat;
  file_path: string | null;
  created_at: string;
  download_url: string | null;
}

export interface ExportHistoryResponse {
  records: ExportRecord[];
  total: number;
}

export interface GenerateReportResponse {
  success: boolean;
  content: string;
  format: ExportFormat;
  filename: string;
}
