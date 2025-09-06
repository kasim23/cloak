import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React, { ReactNode } from 'react';
import { useUploadFile, useProcessDocument, useJobStatus, useGetSuggestions } from '@/hooks/useApi';
import { apiClient } from '@/lib/api';

jest.mock('@/lib/api');
const mockedApiClient = apiClient as jest.Mocked<typeof apiClient>;

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });

  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('useApi hooks', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('useUploadFile', () => {
    it('should upload file successfully', async () => {
      const mockFile = new File(['test'], 'test.txt', { type: 'text/plain' });
      const mockResponse = {
        file_id: 'file-123',
        filename: 'test.txt',
        size: 100,
        content_type: 'text/plain',
      };

      mockedApiClient.uploadFile.mockResolvedValueOnce(mockResponse);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useUploadFile(), { wrapper });

      result.current.mutate(mockFile);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockResponse);
      expect(mockedApiClient.uploadFile).toHaveBeenCalledWith(mockFile);
    });

    it('should handle upload error', async () => {
      const mockFile = new File(['test'], 'test.txt', { type: 'text/plain' });
      const mockError = new Error('Upload failed');

      mockedApiClient.uploadFile.mockRejectedValueOnce(mockError);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useUploadFile(), { wrapper });

      result.current.mutate(mockFile);

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toEqual(mockError);
    });
  });

  describe('useProcessDocument', () => {
    it('should process document successfully', async () => {
      const mockFile = new File(['test'], 'test.txt', { type: 'text/plain' });
      const request = {
        file: mockFile,
        prompt: 'Redact SSN',
        preview_only: false,
      };

      const mockResponse = {
        job_id: 'job-123',
        success: true,
        message: 'Processing started',
        entities_detected: 2,
      };

      mockedApiClient.processDocument.mockResolvedValueOnce(mockResponse);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useProcessDocument(), { wrapper });

      result.current.mutate(request);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockResponse);
      expect(mockedApiClient.processDocument).toHaveBeenCalledWith(request);
    });
  });

  describe('useJobStatus', () => {
    it('should fetch job status successfully', async () => {
      const jobId = 'job-123';
      const mockResponse = {
        job_id: jobId,
        status: 'completed' as const,
        progress: 100,
        result: {
          redacted_file_url: '/download/job-123',
          entities_detected: 3,
        },
      };

      mockedApiClient.getJobStatus.mockResolvedValueOnce(mockResponse);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useJobStatus(jobId), { wrapper });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockResponse);
      expect(mockedApiClient.getJobStatus).toHaveBeenCalledWith(jobId);
    });

    it('should not fetch when jobId is null', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useJobStatus(null), { wrapper });

      expect(result.current.fetchStatus).toBe('idle');
      expect(mockedApiClient.getJobStatus).not.toHaveBeenCalled();
    });

    it('should not fetch when disabled', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useJobStatus('job-123', false), { wrapper });

      expect(result.current.fetchStatus).toBe('idle');
      expect(mockedApiClient.getJobStatus).not.toHaveBeenCalled();
    });
  });

  describe('useGetSuggestions', () => {
    it('should get suggestions successfully', async () => {
      const request = { text_sample: 'John Doe, SSN: 123-45-6789' };
      const mockResponse = {
        suggestions: ['Redact names only', 'Redact SSN only'],
        detected_entities: ['PERSON', 'SSN'],
      };

      mockedApiClient.getSuggestions.mockResolvedValueOnce(mockResponse);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useGetSuggestions(), { wrapper });

      result.current.mutate(request);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockResponse);
      expect(mockedApiClient.getSuggestions).toHaveBeenCalledWith(request);
    });
  });
});