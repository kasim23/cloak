/**
 * @jest-environment jsdom
 */
import MockAdapter from 'axios-mock-adapter';
import {
  RedactionRequest,
  SuggestionsRequest,
} from '@/types/api';

describe('ApiClient', () => {
  let mock: MockAdapter;
  let apiClient: any;

  beforeAll(async () => {
    // Import the apiClient after setting up the environment
    const apiModule = await import('@/lib/api');
    apiClient = apiModule.apiClient;
    
    // Create mock adapter for the internal axios instance
    mock = new MockAdapter(apiClient.axiosInstance);
  });

  beforeEach(() => {
    mock.reset();
  });

  afterAll(() => {
    mock.restore();
  });

  describe('uploadFile', () => {
    it('should upload file successfully', async () => {
      const mockFile = new File(['test content'], 'test.txt', { type: 'text/plain' });
      const mockResponse = {
        file_id: 'test-file-id',
        filename: 'test.txt',
        size: 100,
        content_type: 'text/plain',
      };

      mock.onPost('/upload').reply(200, mockResponse);

      const result = await apiClient.uploadFile(mockFile);

      expect(result).toEqual(mockResponse);
    });

    it('should handle upload errors', async () => {
      const mockFile = new File(['test content'], 'test.txt', { type: 'text/plain' });
      
      mock.onPost('/upload').reply(413, { detail: 'File too large' });

      await expect(apiClient.uploadFile(mockFile)).rejects.toEqual(
        expect.objectContaining({
          message: 'File too large',
          status: 413,
        })
      );
    });
  });

  describe('processDocument', () => {
    it('should process document with all parameters', async () => {
      const mockFile = new File(['test content'], 'test.txt', { type: 'text/plain' });
      const request: RedactionRequest = {
        file: mockFile,
        prompt: 'Redact SSN only',
        preview_only: true,
      };

      const mockResponse = {
        job_id: 'job-123',
        success: true,
        message: 'Processing started',
        entities_detected: 2,
      };

      mock.onPost('/redact').reply(200, mockResponse);

      const result = await apiClient.processDocument(request);
      expect(result).toEqual(mockResponse);
    });

    it('should process document with minimal parameters', async () => {
      const mockFile = new File(['test content'], 'test.txt', { type: 'text/plain' });
      const request: RedactionRequest = {
        file: mockFile,
      };

      const mockResponse = {
        job_id: 'job-456',
        success: true,
        message: 'Processing started',
        entities_detected: 1,
      };

      mock.onPost('/redact').reply(200, mockResponse);

      const result = await apiClient.processDocument(request);
      expect(result).toEqual(mockResponse);
    });
  });

  describe('getJobStatus', () => {
    it('should get job status successfully', async () => {
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

      mock.onGet(`/job/${jobId}/status`).reply(200, mockResponse);

      const result = await apiClient.getJobStatus(jobId);
      expect(result).toEqual(mockResponse);
    });
  });

  describe('downloadResult', () => {
    it('should download result as blob', async () => {
      const jobId = 'job-123';
      const mockBlob = new Blob(['redacted content'], { type: 'text/plain' });

      mock.onGet(`/job/${jobId}/download`).reply(200, mockBlob);

      const result = await apiClient.downloadResult(jobId);
      expect(result).toBeInstanceOf(Blob);
    });
  });

  describe('getSuggestions', () => {
    it('should get suggestions successfully', async () => {
      const request: SuggestionsRequest = {
        text_sample: 'John Doe, SSN: 123-45-6789',
      };

      const mockResponse = {
        suggestions: ['Redact names only', 'Redact SSN only'],
        detected_entities: ['PERSON', 'SSN'],
      };

      mock.onPost('/suggestions').reply(200, mockResponse);

      const result = await apiClient.getSuggestions(request);
      expect(result).toEqual(mockResponse);
    });
  });

  describe('healthCheck', () => {
    it('should check health successfully', async () => {
      const mockResponse = { status: 'healthy' };

      mock.onGet('/health').reply(200, mockResponse);

      const result = await apiClient.healthCheck();
      expect(result).toEqual(mockResponse);
    });
  });

  describe('integration', () => {
    it('should create API client instance without errors', () => {
      expect(apiClient).toBeDefined();
      expect(typeof apiClient.uploadFile).toBe('function');
      expect(typeof apiClient.processDocument).toBe('function');
      expect(typeof apiClient.getJobStatus).toBe('function');
      expect(typeof apiClient.downloadResult).toBe('function');
      expect(typeof apiClient.getSuggestions).toBe('function');
      expect(typeof apiClient.healthCheck).toBe('function');
    });
  });
});