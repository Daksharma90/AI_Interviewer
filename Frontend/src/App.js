import React, { useState } from 'react';
import UploadResume from './components/UploadResume';
import InterviewPanel from './components/InterviewPanel';
import EvaluationReport from './components/EvaluationReport';

function App() {
  const [stage, setStage] = useState('upload');
  const [resumeData, setResumeData] = useState(null);
  const [domain, setDomain] = useState('');
  const [sessionId, setSessionId] = useState(null); 
  const [interviewResult, setInterviewResult] = useState(null);
  const [initialQuestionData, setInitialQuestionData] = useState(null);

  const handleStartInterview = (parsedData, selectedDomain, newSessionId, firstQuestion, firstQuestionAudioRawBase64) => {
    setResumeData(parsedData);
    setDomain(selectedDomain);
    setSessionId(newSessionId);
    
    // CRITICAL FIX: Prepend the data URI prefix to the raw base64 audio string
    const formattedAudioUrl = `data:audio/mpeg;base64,${firstQuestionAudioRawBase64}`;
    
    setInitialQuestionData({ question: firstQuestion, audio_base64: formattedAudioUrl });
    setStage('interview'); 
  };

  const handleEndInterview = (result) => {
    setInterviewResult(result);
    setStage('evaluation');
  };

  const handleRestart = () => {
    setStage('upload');
    setResumeData(null);
    setDomain('');
    setSessionId(null);
    setInterviewResult(null);
    setInitialQuestionData(null);
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-blue-500 to-indigo-600 p-4 font-inter">
      <div className="bg-white rounded-xl shadow-2xl p-8 md:p-12 w-full max-w-4xl transform transition-all duration-500 ease-in-out hover:scale-[1.01] hover:shadow-3xl">
        <h1 className="text-4xl md:text-5xl font-bold text-center mb-10 text-gray-800">
          AI Interviewer
        </h1>

        {stage === 'upload' && (
          <UploadResume onStartInterview={handleStartInterview} />
        )}

        {stage === 'interview' && initialQuestionData && (
          <InterviewPanel
            resumeData={resumeData}
            domain={domain}
            sessionId={sessionId}
            initialQuestion={initialQuestionData.question}
            initialAudioUrl={initialQuestionData.audio_base64} // This will now be a full data URI
            onEndInterview={handleEndInterview}
          />
        )}

        {stage === 'evaluation' && (
          <EvaluationReport
            interviewResult={interviewResult}
            onRestart={handleRestart}
          />
        )}
      </div>
    </div>
  );
}

export default App;
