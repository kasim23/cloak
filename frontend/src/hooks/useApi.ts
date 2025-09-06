import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import {
  RedactionRequest,
  SuggestionsRequest,
} from '@/types/api';

export const useUploadFile = () => {
  return useMutation({
    mutationFn: (file: File) => apiClient.uploadFile(file),
    onError: (error) => {
      console.error('File upload failed:', error);
    },
  });
};

export const useProcessDocument = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (request: RedactionRequest) => apiClient.processDocument(request),
    onSuccess: (data) => {
      if (data.job_id) {
        queryClient.invalidateQueries({ queryKey: ['job-status', data.job_id] });
      }
    },
    onError: (error) => {
      console.error('Document processing failed:', error);
    },
  });
};

export const useJobStatus = (jobId: string | null, enabled: boolean = true) => {
  return useQuery({
    queryKey: ['job-status', jobId],
    queryFn: () => apiClient.getJobStatus(jobId!),
    enabled: enabled && !!jobId,
    refetchInterval: (data) => {
      if (data?.status === 'completed' || data?.status === 'failed') {
        return false;
      }
      return 2000; // Poll every 2 seconds for pending/processing jobs
    },
    retry: 3,
  });
};

export const useDownloadResult = () => {
  return useMutation({
    mutationFn: (jobId: string) => apiClient.downloadResult(jobId),
    onSuccess: (blob, jobId) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `redacted-document-${jobId}.txt`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    },
    onError: (error) => {
      console.error('Download failed:', error);
    },
  });
};

export const useGetSuggestions = () => {
  return useMutation({
    mutationFn: (request: SuggestionsRequest) => apiClient.getSuggestions(request),
    onError: (error) => {
      console.error('Failed to get suggestions:', error);
    },
  });
};

export const useHealthCheck = () => {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => apiClient.healthCheck(),
    retry: 2,
    staleTime: 30000, // 30 seconds
  });
};