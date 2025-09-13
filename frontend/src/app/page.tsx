'use client';

import { FileUpload } from '@/components/FileUpload';
import { Header } from '@/components/Header';

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-white">
      <Header />
      
      <main className="max-w-4xl mx-auto px-6 py-12">
        {/* Hero Section */}
        <div className="text-center mb-16">
          <h1 className="text-4xl md:text-6xl font-light tracking-tight text-gray-900 mb-6">
            Redact documents with
            <span className="block text-transparent bg-clip-text bg-gradient-to-r from-orange-500 to-red-600 font-medium">
              visual precision
            </span>
          </h1>
          
          <p className="text-lg md:text-xl text-gray-600 max-w-2xl mx-auto mb-8 font-light leading-relaxed">
            Privacy-first document redaction using black boxes instead of [REDACTED] text. 
            Customize with natural language like "don't redact names, only SSN".
          </p>
          
          <div className="flex flex-wrap gap-3 justify-center text-sm text-gray-500">
            <div className="flex items-center gap-2 bg-white/80 backdrop-blur-sm px-3 py-1.5 rounded-full border border-gray-200">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              No document storage
            </div>
            <div className="flex items-center gap-2 bg-white/80 backdrop-blur-sm px-3 py-1.5 rounded-full border border-gray-200">
              <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
              Immediate deletion
            </div>
            <div className="flex items-center gap-2 bg-white/80 backdrop-blur-sm px-3 py-1.5 rounded-full border border-gray-200">
              <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
              Natural language
            </div>
          </div>
        </div>

        {/* Upload Section */}
        <div className="bg-white/60 backdrop-blur-sm rounded-2xl border border-gray-200/60 shadow-lg shadow-gray-200/20 p-8">
          <FileUpload />
        </div>

        {/* Features Preview */}
        <div className="mt-20 grid md:grid-cols-3 gap-8">
          <div className="text-center p-6">
            <div className="w-12 h-12 bg-gradient-to-br from-orange-500 to-red-600 rounded-xl flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Visual Redaction</h3>
            <p className="text-gray-600 text-sm">Black boxes over sensitive content, maintaining document structure and readability</p>
          </div>

          <div className="text-center p-6">
            <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Natural Language</h3>
            <p className="text-gray-600 text-sm">Tell it what to redact in plain English: "only hide SSN and phone numbers"</p>
          </div>

          <div className="text-center p-6">
            <div className="w-12 h-12 bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Privacy First</h3>
            <p className="text-gray-600 text-sm">Documents processed locally, never stored on servers, automatic deletion</p>
          </div>
        </div>
      </main>
    </div>
  );
}