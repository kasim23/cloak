'use client';

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';
import { useProcessDocument, useJobStatus, useDownloadResult } from '@/hooks/useApi';
import { ProcessingStatus } from './ProcessingStatus';
import { NaturalLanguageInput } from './NaturalLanguageInput';
import { DocumentPreview } from './DocumentPreview';

interface UploadedFile {
  file: File;
  id: string;
}

export function FileUpload() {
  const [uploadedFile, setUploadedFile] = useState<UploadedFile | null>(null);
  const [prompt, setPrompt] = useState('');
  const [jobId, setJobId] = useState<string | null>(null);
  
  const processDocument = useProcessDocument();
  const { data: jobStatus, isLoading: statusLoading } = useJobStatus(jobId, !!jobId);
  const downloadResult = useDownloadResult();

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;

    // Validate file size (50MB limit)
    const maxSize = 50 * 1024 * 1024; // 50MB
    if (file.size > maxSize) {
      toast.error('File size must be less than 50MB');
      return;
    }

    // Validate file type
    const allowedTypes = [
      'text/plain',
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'image/png',
      'image/jpeg',
      'image/jpg'
    ];
    
    if (!allowedTypes.includes(file.type)) {
      toast.error('Unsupported file type. Please upload .txt, .pdf, .docx, or image files.');
      return;
    }

    const uploadedFile: UploadedFile = {
      file,
      id: Math.random().toString(36).substr(2, 9)
    };

    setUploadedFile(uploadedFile);
    toast.success(`File "${file.name}" ready for processing`);
  }, []);

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: {
      'text/plain': ['.txt'],
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg']
    },
    maxSize: 50 * 1024 * 1024, // 50MB
    multiple: false
  });

  const handleProcess = async () => {
    if (!uploadedFile) return;

    try {
      const result = await processDocument.mutateAsync({
        file: uploadedFile.file,
        prompt: prompt.trim() || undefined,
        preview_only: false
      });

      setJobId(result.job_id);
      toast.success('Document processing started!');
    } catch (error: any) {
      toast.error(error.message || 'Failed to process document');
    }
  };

  const handleDownload = async () => {
    if (!jobId) return;
    
    try {
      await downloadResult.mutateAsync(jobId);
      toast.success('Document downloaded successfully!');
    } catch (error: any) {
      toast.error(error.message || 'Failed to download document');
    }
  };

  const handleReset = () => {
    setUploadedFile(null);
    setPrompt('');
    setJobId(null);
  };

  return (
    <div className="space-y-8">
      <AnimatePresence mode="wait">
        {!uploadedFile ? (
          <motion.div
            key="upload"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            {/* Dropzone */}
            <div
              {...getRootProps()}
              className={`relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-200 ${
                isDragActive && !isDragReject
                  ? 'border-orange-400 bg-orange-50/50 scale-[1.02]'
                  : isDragReject
                  ? 'border-red-400 bg-red-50/50'
                  : 'border-gray-300 hover:border-orange-300 hover:bg-gray-50/50'
              }`}
            >
              <input {...getInputProps()} />
              
              <div className="space-y-4">
                <div className="mx-auto w-16 h-16 bg-gradient-to-br from-orange-500 to-red-600 rounded-2xl flex items-center justify-center">
                  <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                </div>
                
                <div>
                  <p className="text-lg font-medium text-gray-900 mb-2">
                    {isDragActive
                      ? isDragReject
                        ? 'File type not supported'
                        : 'Drop your document here'
                      : 'Upload a document to redact'
                    }
                  </p>
                  <p className="text-gray-500">
                    Supports .txt, .pdf, .docx, and image files up to 50MB
                  </p>
                </div>
                
                <button
                  type="button"
                  className="inline-flex items-center gap-2 bg-gradient-to-r from-orange-500 to-red-600 text-white px-6 py-3 rounded-xl font-medium hover:from-orange-600 hover:to-red-700 transition-all duration-200 shadow-lg shadow-orange-500/25"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                  </svg>
                  Choose File
                </button>
              </div>
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="processing"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="space-y-6"
          >
            {/* File Info */}
            <div className="bg-white/80 backdrop-blur-sm rounded-xl border border-gray-200 p-6">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                    <svg className="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-900">{uploadedFile.file.name}</h3>
                    <p className="text-sm text-gray-500">
                      {(uploadedFile.file.size / (1024 * 1024)).toFixed(2)} MB • {uploadedFile.file.type}
                    </p>
                  </div>
                </div>
                
                <button
                  onClick={handleReset}
                  className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Natural Language Input */}
            <NaturalLanguageInput value={prompt} onChange={setPrompt} />

            {/* Processing Status */}
            {jobId && (
              <ProcessingStatus 
                jobStatus={jobStatus} 
                isLoading={statusLoading} 
                onDownload={handleDownload}
                downloadLoading={downloadResult.isPending}
              />
            )}

            {/* Actions */}
            {!jobId && (
              <div className="flex gap-3">
                <button
                  onClick={handleProcess}
                  disabled={processDocument.isPending}
                  className="flex-1 bg-gradient-to-r from-orange-500 to-red-600 text-white py-3 px-6 rounded-xl font-medium hover:from-orange-600 hover:to-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-lg shadow-orange-500/25"
                >
                  {processDocument.isPending ? (
                    <div className="flex items-center justify-center gap-2">
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                      Processing...
                    </div>
                  ) : (
                    'Start Redaction'
                  )}
                </button>
                
                <button
                  onClick={handleReset}
                  className="px-6 py-3 border border-gray-300 text-gray-700 rounded-xl font-medium hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}