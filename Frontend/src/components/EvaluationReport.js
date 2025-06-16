import React from 'react';
import { ArrowUturnLeftIcon, TrophyIcon, AdjustmentsHorizontalIcon, SparklesIcon } from '@heroicons/react/24/solid';

function EvaluationReport({ interviewResult, onRestart }) {
  if (!interviewResult) {
    return (
      <div className="flex flex-col items-center justify-center p-8 bg-white rounded-lg shadow-xl text-center">
        <p className="text-xl text-gray-700">No evaluation report available. Please complete an interview first.</p>
        <button
          onClick={onRestart}
          className="mt-6 flex items-center px-6 py-3 bg-primary text-white rounded-full shadow-md hover:bg-secondary transition-colors duration-200"
        >
          <ArrowUturnLeftIcon className="h-5 w-5 mr-2" /> Go Back
        </button>
      </div>
    );
  }

  const { overall_performance, weak_points, improvements } = interviewResult;

  return (
    <div className="flex flex-col items-center p-8 bg-white rounded-xl shadow-xl space-y-8 max-w-3xl mx-auto">
      <h2 className="text-4xl font-extrabold text-primary text-center mb-6">Interview Evaluation</h2>

      <div className="w-full bg-blue-50 p-6 rounded-lg border border-blue-200 shadow-inner flex flex-col sm:flex-row items-start sm:items-center">
        <TrophyIcon className="h-10 w-10 text-primary mr-4 mb-3 sm:mb-0 flex-shrink-0" />
        <div>
          <h3 className="text-2xl font-bold text-gray-800 mb-2">Overall Performance</h3>
          <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">{overall_performance}</p>
        </div>
      </div>

      <div className="w-full bg-red-50 p-6 rounded-lg border border-red-200 shadow-inner flex flex-col sm:flex-row items-start sm:items-center">
        <AdjustmentsHorizontalIcon className="h-10 w-10 text-red-500 mr-4 mb-3 sm:mb-0 flex-shrink-0" />
        <div>
          <h3 className="text-2xl font-bold text-gray-800 mb-2">Areas for Improvement</h3>
          <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">{weak_points}</p>
        </div>
      </div>

      <div className="w-full bg-green-50 p-6 rounded-lg border border-green-200 shadow-inner flex flex-col sm:flex-row items-start sm:items-center">
        <SparklesIcon className="h-10 w-10 text-green-500 mr-4 mb-3 sm:mb-0 flex-shrink-0" />
        <div>
          <h3 className="text-2xl font-bold text-gray-800 mb-2">Suggestions for Improvement</h3>
          <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">{improvements}</p>
        </div>
      </div>

      <button
        onClick={onRestart}
        className="mt-8 flex items-center px-8 py-4 bg-primary text-white text-xl font-semibold rounded-full shadow-lg hover:bg-secondary transition-all duration-300 transform hover:scale-105"
      >
        <ArrowUturnLeftIcon className="h-6 w-6 mr-3" /> Start New Interview
      </button>
    </div>
  );
}

export default EvaluationReport;
