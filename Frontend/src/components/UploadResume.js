import React, { useState } from 'react';
import { CloudArrowUpIcon, BriefcaseIcon, AcademicCapIcon, BoltIcon } from '@heroicons/react/24/solid';

/**
 * UploadResume Component
 * Allows candidates to upload their resume file (PDF or DOCX) and
 * select their desired interview domain. It then initiates the interview
 * process by sending this information to the backend.
 * @param {function} onStartInterview - Callback function from parent (App.js)
 * to transition to the interview stage.
 */
function UploadResume({ onStartInterview }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [domain, setDomain] = useState('');
  const [customDomain, setCustomDomain] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleFileChange = (event) => {
    setError('');
    const file = event.target.files[0];
    if (file) {
      const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
      if (allowedTypes.includes(file.type)) {
        setSelectedFile(file);
      } else {
        setSelectedFile(null);
        setError('Unsupported file type. Please upload a PDF or DOCX file.');
      }
    }
  };

  const handleDomainChange = (event) => {
    setDomain(event.target.value);
    if (event.target.value !== 'other') {
      setCustomDomain('');
    }
    setError('');
  };

  const handleCustomDomainChange = (event) => {
    setCustomDomain(event.target.value);
    setDomain('other');
    setError('');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');

    if (!selectedFile) {
      setError('Please select a resume file.');
      return;
    }

    const effectiveDomain = domain === 'other' ? customDomain.trim() : domain;
    if (!effectiveDomain) {
      setError('Please select or enter an interview domain.');
      return;
    }

    setIsLoading(true);

    const formData = new FormData();
    formData.append('resume', selectedFile);
    formData.append('domain', effectiveDomain);

    console.log("Frontend: Sending resume and domain to backend...");

    try {
      const response = await fetch('http://127.0.0.1:8000/start-interview', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to start interview.');
      }

      const data = await response.json();
      console.log('Frontend: Backend response:', data);

      // Pass the raw base64 string to App.js, which will then format it into a data URI
      onStartInterview(
        data.resume_info,
        effectiveDomain,
        data.session_id,
        data.question,
        data.audio_base64 // This is the raw base64 string from the backend
      );
    } catch (err) {
      console.error('Frontend Error: Error starting interview:', err);
      setError(err.message || 'An unexpected error occurred. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-md relative" role="alert">
          <span className="block sm:inline">{error}</span>
        </div>
      )}

      <div className="flex items-center justify-center w-full">
        <label
          htmlFor="dropzone-file"
          className="flex flex-col items-center justify-center w-full h-48 border-2 border-gray-300 border-dashed rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100 transition-colors duration-200"
        >
          <div className="flex flex-col items-center justify-center pt-5 pb-6">
            <CloudArrowUpIcon className="w-10 h-10 mb-3 text-gray-400" />
            <p className="mb-2 text-sm text-gray-500">
              <span className="font-semibold">Click to upload</span> or drag and drop
            </p>            
            <p className="text-xs text-gray-500 px-4 text-center">
              The interview will start with an audio question. Your microphone will automatically start recording after the question. You'll have up to 5 minutes to answer or you can submit your answer sooner.
            </p>            
            <p className="text-xs text-gray-500">PDF or DOCX (Max 5MB)</p>
            {selectedFile && (
              <p className="mt-2 text-sm text-blue-600">Selected: {selectedFile.name}</p>
            )}
          </div>
          <input
            id="dropzone-file"
            type="file"
            className="hidden"
            onChange={handleFileChange}
            accept=".pdf,.docx"
          />
        </label>
      </div>

      <div className="mt-6">
        <label htmlFor="domain-select" className="block text-sm font-medium text-gray-700 mb-2">
          Select Interview Domain:
        </label>
        <select
          id="domain-select"
          name="domain"
          value={domain}
          onChange={handleDomainChange}
          className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-primary focus:border-primary sm:text-sm rounded-md shadow-sm"
        >
          <option value="">-- Choose a domain --</option>
          <option value="Software Engineering">
            <BriefcaseIcon className="inline-block h-4 w-4 mr-1" /> Software Engineering
          </option>
          <option value="Data Science">
            <AcademicCapIcon className="inline-block h-4 w-4 mr-1" /> Data Science
          </option>
          <option value="Product Management">
            <BoltIcon className="inline-block h-4 w-4 mr-1" /> Product Management
          </option>
          <option value="HR">HR Interview</option>
          <option value="other">Other (Specify below)</option>
        </select>

        {domain === 'other' && (
          <input
            type="text"
            value={customDomain}
            onChange={handleCustomDomainChange}
            placeholder="e.g., UX Design, Marketing, Finance"
            className="mt-3 block w-full shadow-sm sm:text-sm border-gray-300 rounded-md p-2 focus:ring-primary focus:border-primary"
          />
        )}
      </div>

      <button
        type="submit"
        disabled={isLoading || !selectedFile || !(domain || customDomain.trim())}
        className="w-full flex items-center justify-center px-6 py-3 border border-transparent rounded-md shadow-sm text-lg font-semibold text-white bg-primary hover:bg-secondary focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isLoading ? (
          <>
            <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Starting Interview...
          </>
        ) : (
          'Start Interview'
        )}
      </button>
    </form>
  );
}

export default UploadResume;
