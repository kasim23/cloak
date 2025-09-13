import axios, { AxiosInstance, AxiosError } from 'axios';
import {
  RedactionRequest,
  RedactionResponse,
  JobStatusResponse,
  SuggestionsRequest,
  SuggestionsResponse,
  UploadResponse,
  ErrorResponse,
  AnalyzePromptRequest,
  AnalyzePromptResponse,
} from '@/types/api';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
      timeout: parseInt(process.env.NEXT_PUBLIC_API_TIMEOUT || '30000'),
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    this.client.interceptors.request.use(
      (config) => {
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<ErrorResponse>) => {
        const customError = {
          message: error.response?.data?.detail || error.message || 'An error occurred',
          status: error.response?.status || 500,
          originalError: error,
        };
        return Promise.reject(customError);
      }
    );
  }

  async uploadFile(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await this.client.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  }

  async processDocument(request: RedactionRequest): Promise<RedactionResponse> {
    const formData = new FormData();
    formData.append('file', request.file);
    
    if (request.prompt) {
      formData.append('prompt', request.prompt);
    }
    
    if (request.preview_only !== undefined) {
      formData.append('preview_only', request.preview_only.toString());
    }

    const response = await this.client.post('/redact', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  }

  async getJobStatus(jobId: string): Promise<JobStatusResponse> {
    const response = await this.client.get(`/job/${jobId}/status`);
    return response.data;
  }

  async downloadResult(jobId: string): Promise<Blob> {
    const response = await this.client.get(`/job/${jobId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  }

  async getSuggestions(request: SuggestionsRequest): Promise<SuggestionsResponse> {
    const response = await this.client.post('/suggestions', request);
    return response.data;
  }

  async analyzePrompt(request: AnalyzePromptRequest): Promise<AnalyzePromptResponse> {
    const response = await this.client.post('/analyze-prompt', request);
    return response.data;
  }

  async healthCheck(): Promise<{ status: string }> {
    const response = await this.client.get('/health');
    return response.data;
  }

  // Getter for testing purposes
  get axiosInstance() {
    return this.client;
  }
}

export const apiClient = new ApiClient();
export default apiClient;