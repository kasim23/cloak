'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { AnalyzePromptResponse } from '@/types/api';

interface EntityDetectionPreviewProps {
  analysis?: AnalyzePromptResponse;
  isLoading?: boolean;
  prompt: string;
}

export function EntityDetectionPreview({ analysis, isLoading, prompt }: EntityDetectionPreviewProps) {
  if (!prompt.trim() || (!analysis && !isLoading)) {
    return null;
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, height: 0 }}
        animate={{ opacity: 1, height: 'auto' }}
        exit={{ opacity: 0, height: 0 }}
        transition={{ duration: 0.2 }}
        className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden"
      >
        <div className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <div className={`w-2 h-2 rounded-full ${
              isLoading 
                ? 'bg-yellow-500 animate-pulse' 
                : analysis?.confidence === 'high' 
                  ? 'bg-green-500' 
                  : analysis?.confidence === 'low'
                    ? 'bg-red-500'
                    : 'bg-blue-500'
            }`}></div>
            <h4 className="text-sm font-medium text-gray-900">
              {isLoading ? 'Analyzing prompt...' : 'What Cloak understood:'}
            </h4>
            {analysis?.confidence && (
              <span className={`text-xs px-2 py-0.5 rounded-full ${
                analysis.confidence === 'high' 
                  ? 'bg-green-100 text-green-700'
                  : analysis.confidence === 'low'
                    ? 'bg-red-100 text-red-700'
                    : 'bg-blue-100 text-blue-700'
              }`}>
                {analysis.confidence} confidence
              </span>
            )}
          </div>

          {isLoading ? (
            <div className="space-y-2">
              <div className="h-4 bg-gray-200 rounded animate-pulse"></div>
              <div className="h-4 bg-gray-200 rounded w-3/4 animate-pulse"></div>
            </div>
          ) : analysis ? (
            <div className="space-y-3">
              {/* Entities to Redact */}
              {analysis.entities_to_redact.length > 0 && (
                <div className="flex items-start gap-3">
                  <div className="flex items-center gap-2 min-w-0">
                    <svg className="w-4 h-4 text-red-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L12 12m-2.122-2.122L7.757 7.757M12 12l2.121 2.121M12 12L9.879 9.879" />
                    </svg>
                    <span className="text-sm font-medium text-red-700">Will redact:</span>
                  </div>
                  <div className="flex flex-wrap gap-1 min-w-0">
                    {analysis.entities_to_redact.map((entity, index) => (
                      <span
                        key={index}
                        className="inline-flex items-center px-2 py-1 text-xs bg-red-100 text-red-700 rounded-md"
                      >
                        {entity.toLowerCase().replace('_', ' ')}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Entities to Keep */}
              {analysis.entities_to_keep.length > 0 && (
                <div className="flex items-start gap-3">
                  <div className="flex items-center gap-2 min-w-0">
                    <svg className="w-4 h-4 text-green-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="text-sm font-medium text-green-700">Will keep:</span>
                  </div>
                  <div className="flex flex-wrap gap-1 min-w-0">
                    {analysis.entities_to_keep.map((entity, index) => (
                      <span
                        key={index}
                        className="inline-flex items-center px-2 py-1 text-xs bg-green-100 text-green-700 rounded-md"
                      >
                        {entity.toLowerCase().replace('_', ' ')}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Unrecognized Terms */}
              {analysis.unrecognized_terms && analysis.unrecognized_terms.length > 0 && (
                <div className="flex items-start gap-3">
                  <div className="flex items-center gap-2 min-w-0">
                    <svg className="w-4 h-4 text-yellow-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.732 15.5c-.77.833.192 2.5 1.732 2.5z" />
                    </svg>
                    <span className="text-sm font-medium text-yellow-700">Unrecognized:</span>
                  </div>
                  <div className="flex flex-wrap gap-1 min-w-0">
                    {analysis.unrecognized_terms.map((term, index) => (
                      <span
                        key={index}
                        className="inline-flex items-center px-2 py-1 text-xs bg-yellow-100 text-yellow-700 rounded-md"
                      >
                        {term}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* No entities detected */}
              {analysis.entities_to_redact.length === 0 && 
               analysis.entities_to_keep.length === 0 && 
               (!analysis.unrecognized_terms || analysis.unrecognized_terms.length === 0) && (
                <div className="flex items-center gap-2 text-sm text-gray-500">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Will redact all detected sensitive information (default behavior)
                </div>
              )}

              {/* Error message */}
              {analysis.error && (
                <div className="flex items-center gap-2 text-sm text-red-600">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Failed to analyze prompt: {analysis.error}
                </div>
              )}
            </div>
          ) : null}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}