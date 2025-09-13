'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAnalyzePrompt } from '@/hooks/useApi';
import { EntityDetectionPreview } from './EntityDetectionPreview';

interface NaturalLanguageInputProps {
  value: string;
  onChange: (value: string) => void;
}

const EXAMPLE_PROMPTS = [
  "Don't redact names, only SSN and credit cards",
  "Hide all personal info but keep company names", 
  "Only redact phone numbers and email addresses",
  "Remove SSN and addresses but keep names",
  "Redact everything except dates"
];

export function NaturalLanguageInput({ value, onChange }: NaturalLanguageInputProps) {
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [debouncedValue, setDebouncedValue] = useState(value);
  
  const analyzePrompt = useAnalyzePrompt();

  // Debounce the prompt value to avoid excessive API calls
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, 500); // 500ms delay

    return () => {
      clearTimeout(handler);
    };
  }, [value]);

  // Analyze the prompt when debounced value changes
  useEffect(() => {
    if (debouncedValue.trim().length > 3) {
      analyzePrompt.mutate({ prompt: debouncedValue });
    }
  }, [debouncedValue]);

  const handleSuggestionClick = (prompt: string) => {
    onChange(prompt);
    setShowSuggestions(false);
  };

  return (
    <div className="space-y-3">
      <div className="relative">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Customization (optional)
        </label>
        
        <div className="relative">
          <textarea
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onFocus={() => setShowSuggestions(true)}
            placeholder="Tell Cloak what to redact in plain English..."
            className="w-full px-4 py-3 pr-12 border border-gray-200 rounded-xl resize-none focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all duration-200 placeholder:text-gray-400 text-gray-900"
            rows={3}
          />
          
          <button
            type="button"
            onClick={() => setShowSuggestions(!showSuggestions)}
            className="absolute top-3 right-3 p-1.5 text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </button>
        </div>
        
        <p className="text-xs text-gray-500 mt-2">
          Leave empty to redact all detected sensitive information, or describe what you want to keep/hide
        </p>
      </div>

      {/* Real-time entity detection preview */}
      <EntityDetectionPreview 
        analysis={analyzePrompt.data}
        isLoading={analyzePrompt.isPending}
        prompt={value}
      />

      <AnimatePresence>
        {showSuggestions && (
          <motion.div
            initial={{ opacity: 0, y: -10, height: 0 }}
            animate={{ opacity: 1, y: 0, height: 'auto' }}
            exit={{ opacity: 0, y: -10, height: 0 }}
            transition={{ duration: 0.2 }}
            className="bg-white rounded-xl border border-gray-200 shadow-lg shadow-gray-200/50 overflow-hidden"
          >
            <div className="p-4">
              <h4 className="text-sm font-medium text-gray-900 mb-3">Example prompts:</h4>
              <div className="space-y-2">
                {EXAMPLE_PROMPTS.map((prompt, index) => (
                  <button
                    key={index}
                    onClick={() => handleSuggestionClick(prompt)}
                    className="w-full text-left text-sm text-gray-600 hover:text-gray-900 py-2 px-3 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    "{prompt}"
                  </button>
                ))}
              </div>
            </div>
            
            <div className="border-t border-gray-100 p-3 bg-gray-50/50">
              <button
                onClick={() => setShowSuggestions(false)}
                className="text-xs text-gray-500 hover:text-gray-700 transition-colors"
              >
                Close suggestions
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}