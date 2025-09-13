'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { JobStatusResponse } from '@/types/api';

interface ProcessingStatusProps {
  jobStatus?: JobStatusResponse;
  isLoading: boolean;
  onDownload: () => void;
  downloadLoading: boolean;
}

// Fun processing messages that rotate every 2-3 seconds
const PROCESSING_MESSAGES = {
  initializing: [
    { text: "🎭 Skidaddling through document...", emoji: "🎭" },
    { text: "🎪 Preparing the hullabaloo...", emoji: "🎪" },
    { text: "✨ Warming up the magic...", emoji: "✨" },
    { text: "🎨 Calibrating the widgets...", emoji: "🎨" }
  ],
  pending: [
    { text: "🕰️ Queuing up the shenanigans...", emoji: "🕰️" },
    { text: "🎯 Taking a number...", emoji: "🎯" },
    { text: "🎪 Waiting for the spotlight...", emoji: "🎪" },
    { text: "⏳ Practicing patience...", emoji: "⏳" }
  ],
  processing: [
    { text: "🕵️ Canoodling with sensitive data...", emoji: "🕵️" },
    { text: "🔍 Sleuthing through paragraphs...", emoji: "🔍" },
    { text: "🎪 Bamboozling PII patterns...", emoji: "🎪" },
    { text: "🎭 Investigating the rascals...", emoji: "🎭" },
    { text: "🎨 Shenaniganing redaction boxes...", emoji: "🎨" },
    { text: "✨ Applying privacy magic...", emoji: "✨" }
  ],
  finalizing: [
    { text: "🎁 Wrapping up the package...", emoji: "🎁" },
    { text: "✨ Polishing the masterpiece...", emoji: "✨" },
    { text: "🎪 Finalizing the hullabaloo...", emoji: "🎪" },
    { text: "🎨 Adding the finishing touches...", emoji: "🎨" }
  ]
};

export function ProcessingStatus({ jobStatus, isLoading, onDownload, downloadLoading }: ProcessingStatusProps) {
  const [currentMessageIndex, setCurrentMessageIndex] = useState(0);

  // Rotate messages every 2.5 seconds
  useEffect(() => {
    if (!jobStatus || jobStatus.status === 'completed' || jobStatus.status === 'failed') {
      return;
    }

    const getMessagesForStatus = () => {
      if (isLoading || !jobStatus) return PROCESSING_MESSAGES.initializing;
      
      switch (jobStatus.status) {
        case 'pending': return PROCESSING_MESSAGES.pending;
        case 'processing': 
          return jobStatus.progress > 80 
            ? PROCESSING_MESSAGES.finalizing 
            : PROCESSING_MESSAGES.processing;
        default: return PROCESSING_MESSAGES.processing;
      }
    };

    const messages = getMessagesForStatus();
    const interval = setInterval(() => {
      setCurrentMessageIndex(prev => (prev + 1) % messages.length);
    }, 2500);

    return () => clearInterval(interval);
  }, [jobStatus, isLoading]);

  if (isLoading || !jobStatus) {
    const currentMessage = PROCESSING_MESSAGES.initializing[currentMessageIndex];
    
    return (
      <div className="bg-white/80 backdrop-blur-sm rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 border-2 border-orange-500/30 border-t-orange-500 rounded-full animate-spin"></div>
          <div>
            <motion.h3 
              key={currentMessageIndex}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="font-medium text-gray-900"
            >
              {currentMessage.text}
            </motion.h3>
            <p className="text-sm text-gray-500">Initializing redaction pipeline</p>
          </div>
        </div>
      </div>
    );
  }

  const getStatusInfo = () => {
    const getMessagesForStatus = () => {
      switch (jobStatus.status) {
        case 'pending': return PROCESSING_MESSAGES.pending;
        case 'processing': 
          return jobStatus.progress > 80 
            ? PROCESSING_MESSAGES.finalizing 
            : PROCESSING_MESSAGES.processing;
        default: return PROCESSING_MESSAGES.processing;
      }
    };

    const currentMessage = (jobStatus.status === 'pending' || jobStatus.status === 'processing') 
      ? getMessagesForStatus()[currentMessageIndex] 
      : null;

    switch (jobStatus.status) {
      case 'pending':
        return {
          icon: (
            <div className="w-8 h-8 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
          ),
          title: currentMessage?.text || 'Queued for Processing',
          description: 'Your document is in the queue',
          color: 'blue'
        };
      case 'processing':
        return {
          icon: (
            <div className="w-8 h-8 border-2 border-orange-500/30 border-t-orange-500 rounded-full animate-spin"></div>
          ),
          title: currentMessage?.text || 'Processing Document',
          description: 'Detecting and redacting sensitive information',
          color: 'orange'
        };
      case 'completed':
        return {
          icon: (
            <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
          ),
          title: '🎉 Processing Complete!',
          description: `Found and redacted ${jobStatus.result?.entities_detected || 0} sensitive items`,
          color: 'green'
        };
      case 'failed':
        return {
          icon: (
            <div className="w-8 h-8 bg-red-500 rounded-full flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
          ),
          title: '😞 Processing Failed',
          description: jobStatus.error || 'An error occurred during processing',
          color: 'red'
        };
      default:
        return {
          icon: <div className="w-8 h-8 bg-gray-300 rounded-full"></div>,
          title: 'Unknown Status',
          description: 'Please refresh the page',
          color: 'gray'
        };
    }
  };

  const statusInfo = getStatusInfo();

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white/80 backdrop-blur-sm rounded-xl border border-gray-200 p-6"
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          {statusInfo.icon}
          <div>
            <motion.h3
              key={`${jobStatus.status}-${currentMessageIndex}`}
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="font-medium text-gray-900"
            >
              {statusInfo.title}
            </motion.h3>
            <p className="text-sm text-gray-500">{statusInfo.description}</p>
            
            {/* Progress bar */}
            {jobStatus.status === 'processing' && (
              <div className="mt-3 w-64">
                <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-gradient-to-r from-orange-500 to-red-600"
                    initial={{ width: '0%' }}
                    animate={{ width: `${jobStatus.progress}%` }}
                    transition={{ duration: 0.5 }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">{jobStatus.progress}% complete</p>
              </div>
            )}
          </div>
        </div>

        {/* Download button */}
        {jobStatus.status === 'completed' && (
          <button
            onClick={onDownload}
            disabled={downloadLoading}
            className="inline-flex items-center gap-2 bg-gradient-to-r from-green-500 to-emerald-600 text-white px-4 py-2 rounded-lg font-medium hover:from-green-600 hover:to-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-lg shadow-green-500/25"
          >
            {downloadLoading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                Downloading...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Download Result
              </>
            )}
          </button>
        )}
      </div>

      {/* Job ID for reference */}
      <div className="mt-4 pt-4 border-t border-gray-100">
        <p className="text-xs text-gray-400">
          Job ID: <code className="font-mono">{jobStatus.job_id}</code>
        </p>
      </div>
    </motion.div>
  );
}