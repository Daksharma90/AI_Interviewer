import React, { useState, useEffect, useRef, useCallback } from 'react';
import { StopIcon, ArrowPathIcon, SpeakerWaveIcon, HandRaisedIcon } from '@heroicons/react/24/solid';

const INTERVIEW_TIME_LIMIT_MS = 5 * 60 * 1000; // 5 minutes

function InterviewPanel({ sessionId, initialQuestion, initialAudioUrl, onEndInterview }) {
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [questionAudioUrl, setQuestionAudioUrl] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [interviewStatus, setInterviewStatus] = useState('Preparing interview...');
  const [error, setError] = useState('');
  const [interviewComplete, setInterviewComplete] = useState(false);
  const [isAudioPlaying, setIsAudioPlaying] = useState(false);
  const [timeLeft, setTimeLeft] = useState(INTERVIEW_TIME_LIMIT_MS / 1000);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const answerTimerRef = useRef(null);
  const countdownIntervalRef = useRef(null);
  const audioRef = useRef(new Audio());
  const audioPlayedForCurrentQuestionRef = useRef(false); // Tracks if play has been ATTEMPTED for the current audio

  // --- Timer Management ---
  const clearAnswerTimer = useCallback(() => {
    clearTimeout(answerTimerRef.current);
    clearInterval(countdownIntervalRef.current);
    answerTimerRef.current = null;
    countdownIntervalRef.current = null;
    setTimeLeft(INTERVIEW_TIME_LIMIT_MS / 1000);
    console.log("Frontend: Answer timer and countdown cleared.");
  }, []);

  // --- API Interaction ---
  const sendAnswerToServer = useCallback(async (audioBlob, isTimeout = false, forceEnd = false) => {
    setIsLoading(true);
    setInterviewStatus("Processing your answer...");
    setError('');

    const formData = new FormData();
    if (audioBlob && audioBlob.size > 0) {
      formData.append('audio_file', audioBlob, 'answer.webm');
    }
    formData.append('session_id', sessionId);
    formData.append('question_id', currentQuestion?.id);
    formData.append('is_timeout', isTimeout);
    formData.append('force_end', forceEnd);

    console.log("Frontend: Sending answer. Timeout:", isTimeout, "Force End:", forceEnd, "Question ID:", currentQuestion?.id);
    let responseData = null;
    try {
      const response = await fetch('http://127.0.0.1:8000/submit-answer', {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to submit answer.');
      }
      responseData = await response.json();
      console.log('Frontend: Submit answer response:', responseData);
      setTranscript(responseData.transcript || (isTimeout ? 'Answer timed out.' : 'No speech detected.'));
      setInterviewStatus(responseData.message || 'Answer processed.');

      if (responseData.next_action === 'next_question' && responseData.question) {
        setCurrentQuestion(responseData.question);
        setQuestionAudioUrl(`data:audio/mpeg;base64,${responseData.audio_base64}`);
        setIsRecording(false); // Reset for next question
        audioPlayedForCurrentQuestionRef.current = false; // Reset for the new question's audio
      } else if (responseData.next_action === 'end_interview') {
        setInterviewComplete(true);
        onEndInterview(responseData.overall_evaluation);
      }
    } catch (err) {
      console.error('Frontend Error: Error sending answer:', err);
      setError(err.message || 'An unexpected error occurred.');
      setInterviewStatus("Interview interrupted due to an error.");
      setIsRecording(false);
    } finally {
      if (!(responseData && responseData.next_action === 'next_question' && responseData.question) && !interviewComplete) {
        setIsLoading(false);
      }
      console.log("Frontend: Finished sending answer processing.");
    }
  }, [sessionId, currentQuestion, onEndInterview]);

  // --- Recording and Timer Logic ---
  const handleStopAndSubmit = useCallback((isTimeout = false, forceEnd = false) => {
    console.log(`Frontend: handleStopAndSubmit called. isTimeout: ${isTimeout}, forceEnd: ${forceEnd}, isRecording: ${isRecording}`);
    clearAnswerTimer();

    if (isRecording && mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.onstop = () => {
        const audioBlob = audioChunksRef.current.length > 0 ? new Blob(audioChunksRef.current, { type: 'audio/webm' }) : null;
        if (mediaRecorderRef.current && mediaRecorderRef.current.stream) {
            mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
        }
        console.log(`Frontend: Recording stopped. Submitting. Timeout: ${isTimeout}, Force End: ${forceEnd}`);
        sendAnswerToServer(audioBlob, isTimeout, forceEnd);
        audioChunksRef.current = [];
        if (mediaRecorderRef.current) mediaRecorderRef.current.onstop = null;
      };
      mediaRecorderRef.current.stop();
    } else {
      const audioBlob = audioChunksRef.current.length > 0 ? new Blob(audioChunksRef.current, { type: 'audio/webm' }) : null;
      console.log(`Frontend: Not actively recording, but submitting. Timeout: ${isTimeout}, Force End: ${forceEnd}`);
      sendAnswerToServer(audioBlob, isTimeout, forceEnd);
      audioChunksRef.current = [];
    }
    setIsRecording(false);
  }, [isRecording, clearAnswerTimer, sendAnswerToServer]);

  const startAnswerTimer = useCallback(() => {
    clearAnswerTimer();
    setTimeLeft(INTERVIEW_TIME_LIMIT_MS / 1000);
    console.log("Frontend: Starting answer timer.");

    countdownIntervalRef.current = setInterval(() => {
      setTimeLeft(prevTime => {
        if (prevTime <= 1) {
          clearInterval(countdownIntervalRef.current);
          countdownIntervalRef.current = null;
          return 0;
        }
        return prevTime - 1;
      });
    }, 1000);

    answerTimerRef.current = setTimeout(() => {
      console.log("Frontend: Answer timer expired.");
      handleStopAndSubmit(true, false);
    }, INTERVIEW_TIME_LIMIT_MS);
  }, [clearAnswerTimer, handleStopAndSubmit]);

  const startRecording = useCallback(async () => {
    // Use current state values directly in guards
    // isLoading should be false by the time we reach here if called from handleAudioEnded
    // isAudioPlaying should also be false
    if (isRecording || interviewComplete) { // Simplified guard
        console.log("Frontend: Start recording pre-condition failed.", {isRecording, isLoading, interviewComplete, isAudioPlaying});
        return;
    }

    setTranscript('');
    audioChunksRef.current = [];
    console.log("Frontend: Attempting to start recording...");

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };
      mediaRecorderRef.current.onstop = () => {
        console.log("Frontend: MediaRecorder stopped (onstop event). Stream tracks stopping.");
        if (mediaRecorderRef.current && mediaRecorderRef.current.stream) {
            mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
        }
      };
      mediaRecorderRef.current.start();
      setIsRecording(true);
      setInterviewStatus("Listening... You have up to 5 minutes. Click 'Submit Answer' when done.");
      setError(''); // Clear any previous errors like "autoplay failed"
      startAnswerTimer();
    } catch (err) {
      console.error('Frontend Error: Error accessing microphone:', err);
      setError('Could not access microphone. Please ensure it is connected and permissions are granted.');
      setInterviewStatus("Microphone access failed. Please check permissions.");
      setIsRecording(false);
    }
  // Dependencies for startRecording:
  // - interviewComplete: to prevent starting if interview is over.
  // - startAnswerTimer: it calls this function.
  // We are intentionally leaving out isRecording, isLoading, isAudioPlaying from deps
  // to make startRecording more stable and rely on the calling context (handleAudioEnded) to ensure preconditions.
  }, [interviewComplete, startAnswerTimer]);
  // Effect to initialize the first question
  useEffect(() => {
    // This effect should only run when initialQuestion or initialAudioUrl actually change identity
    if (initialQuestion && initialAudioUrl) {
      console.log("Frontend: Initializing with first question:", initialQuestion.id, "Current audioPlayedRef:", audioPlayedForCurrentQuestionRef.current);
      // Only update if the question is genuinely new or the component is just mounting
      if (currentQuestion?.id !== initialQuestion.id || !currentQuestion) {
        setCurrentQuestion(initialQuestion);
        setQuestionAudioUrl(initialAudioUrl);
        setInterviewStatus("First question loaded. Preparing to play audio...");
        setIsLoading(false); // Ready to attempt playing
        audioPlayedForCurrentQuestionRef.current = false; // Reset for this new initial question
        setIsAudioPlaying(false); // Ensure this is reset
        setIsRecording(false); // Ensure this is reset
        setError(''); // Clear any previous errors
      }
    } else {
      setInterviewStatus("Waiting for initial interview data...");
      setIsLoading(true);
    }
  }, [initialQuestion, initialAudioUrl]); // Keep currentQuestion out to avoid loop if parent re-renders initialQuestion with same ID but new object

  // Effect to play question audio when questionAudioUrl changes
  useEffect(() => {
    const audio = audioRef.current;

    if (!questionAudioUrl || interviewComplete || isRecording || audioPlayedForCurrentQuestionRef.current) {
      console.log("Frontend: Audio effect guard triggered. Bailing out.", { questionAudioUrl: !!questionAudioUrl, interviewComplete, isRecording, audioPlayedRef: audioPlayedForCurrentQuestionRef.current });
      if (isLoading && !isAudioPlaying && !isRecording && !interviewComplete) {
          setIsLoading(false); // Ensure loading is false if we are not going to play
      }
      return;
    }

    console.log("Frontend: Audio effect - Setting up for question:", currentQuestion?.id);
    setIsLoading(true); // We are about to load/play
    setInterviewStatus("Loading question audio...");
    audio.src = questionAudioUrl;
    audio.load();

    const handleCanPlayThrough = () => {
      console.log("Frontend: Audio can play through for:", currentQuestion?.id);
      if (audio.paused && !isAudioPlaying && !interviewComplete && !isRecording && !audioPlayedForCurrentQuestionRef.current) {
        audioPlayedForCurrentQuestionRef.current = true; // Mark as attempted to play
        audio.play()
          .then(() => {
            console.log("Frontend: Audio playback initiated successfully for:", currentQuestion?.id);
            setIsAudioPlaying(true);
            setIsLoading(false);
            setInterviewStatus("Playing question...");
          })
          .catch(error => {
            console.error("Frontend Error: Autoplay failed for:", currentQuestion?.id, error);
            setError("Audio could not autoplay. Please click 'Play/Replay Question'.");
            setInterviewStatus("Question ready. Click 'Play/Replay Question' to start.");
            setIsAudioPlaying(false);
            setIsLoading(false);
            audioPlayedForCurrentQuestionRef.current = false; // Reset if autoplay specifically failed
          });
      } else {
        console.log("Frontend: Autoplay conditions not met or audio already handled for:", currentQuestion?.id, {paused: audio.paused, isAudioPlaying, interviewComplete, isRecording, playedRef: audioPlayedForCurrentQuestionRef.current});
        if (isLoading && !isAudioPlaying) setIsLoading(false);
      }
    };

    const handleAudioEnded = () => {
      console.log("Frontend: Audio ended for:", currentQuestion?.id);
      setIsAudioPlaying(false);
      setIsLoading(false); // Crucial: Ensure isLoading is false before attempting to record
      if (!interviewComplete && !isRecording) {
        setInterviewStatus("Question finished. Recording your answer...");
        startRecording();
      }
    };

    const handleError = (e) => {
      console.error("Frontend Error: Audio element error:", e, audio.error);
      setError("Error loading or playing question audio.");
      setInterviewStatus("Error with question audio.");
      setIsAudioPlaying(false);
      setIsLoading(false);
      audioPlayedForCurrentQuestionRef.current = false; // Allow retry
    };

    audio.addEventListener('canplaythrough', handleCanPlayThrough);
    audio.addEventListener('ended', handleAudioEnded);
    audio.addEventListener('error', handleError);

    return () => {
      console.log("Frontend: Cleaning up audio effect for:", currentQuestion?.id);
      audio.removeEventListener('canplaythrough', handleCanPlayThrough);
      audio.removeEventListener('ended', handleAudioEnded);
      audio.removeEventListener('error', handleError);
      if (audio.src && !audio.paused) {
        audio.pause();
      }
      audio.currentTime = 0;
    };
  // Dependencies:
  // - questionAudioUrl: Main trigger for new audio.
  // - interviewComplete: To stop processing if the interview ends.
  // - currentQuestion: For logging and context.
  // - startRecording: The stable callback to call on 'ended'.
  // - isRecording: Guard condition in the effect.
  }, [questionAudioUrl, interviewComplete, currentQuestion, startRecording, isRecording]);

  // --- User Actions ---
  const playOrReplayQuestionAudio = useCallback(() => {
    const audio = audioRef.current;
    if (audio.src && !isLoading && !isRecording && !isAudioPlaying) {
      console.log("Frontend: Attempting to play/replay question audio manually.");
      audio.currentTime = 0;
      audioPlayedForCurrentQuestionRef.current = true; // Mark as played/attempted
      const playPromise = audio.play();
      if (playPromise !== undefined) {
        setIsAudioPlaying(true);
        setInterviewStatus("Playing question...");
        playPromise.catch(e => {
          console.error("Frontend Error: Manual audio playback error:", e);
          setError("Could not play audio. Please try again or check browser permissions.");
          setInterviewStatus("Error playing audio.");
          setIsAudioPlaying(false);
          audioPlayedForCurrentQuestionRef.current = false; // Reset if manual play failed
        });
      }
    } else {
      console.log("Frontend: Cannot play/replay. Conditions:", { src: !!audio.src, isLoading, isRecording, isAudioPlaying });
      setError("Cannot play audio now. System might be busy, recording, or audio is already playing.");
    }
  }, [isLoading, isRecording, isAudioPlaying]);


  if (interviewComplete) {
    return (
      <div className="flex flex-col items-center justify-center p-8 bg-white rounded-lg shadow-xl text-center">
        <h2 className="text-3xl font-bold text-primary mb-4">Interview Completed!</h2>
        <p className="text-lg text-gray-700 mb-6">Generating your evaluation report...</p>
        <ArrowPathIcon className="h-12 w-12 text-blue-400 animate-spin" />
      </div>
    );
  }

  const formatTime = (seconds) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds < 10 ? '0' : ''}${remainingSeconds}`;
  };

  return (
    <div className="flex flex-col items-center p-6 md:p-8 bg-white rounded-xl shadow-xl space-y-6 max-w-2xl mx-auto">
      <h2 className="text-2xl md:text-3xl font-extrabold text-gray-800 text-center">Interview in Progress</h2>
      <p className="text-sm text-gray-500 text-center">Session ID: {sessionId?.substring(0,8)}...</p>

      <div className="w-full bg-gray-100 p-6 rounded-lg border border-gray-200 shadow-inner min-h-[120px] flex flex-col justify-center items-center relative">
        {isLoading && !error && !currentQuestion?.text ? (
          <div className="flex flex-col items-center">
            <ArrowPathIcon className="h-10 w-10 text-blue-500 animate-spin mb-4" />
            <p className="text-gray-600 text-lg font-medium">{interviewStatus}</p>
          </div>
        ) : error ? (
          <p className="text-red-600 text-lg font-medium text-center p-4">{error}</p>
        ) : (
          <>
            <p className="text-lg md:text-xl font-semibold text-gray-800 text-center mb-4">
              {currentQuestion?.text || 'Loading question...'}
            </p>
            {questionAudioUrl && !isRecording && !isAudioPlaying && !isLoading && currentQuestion && (
              <button
                onClick={playOrReplayQuestionAudio}
                disabled={!currentQuestion || isLoading}
                className="flex items-center px-4 py-2 bg-blue-500 text-white rounded-full shadow-md hover:bg-blue-600 transition-colors duration-200 text-sm disabled:opacity-60"
              >
                <SpeakerWaveIcon className="h-5 w-5 mr-2" />
                {audioRef.current.currentTime > 0 ? 'Replay Question' : 'Play Question'}
              </button>
            )}
             {isAudioPlaying && <p className="text-sm text-blue-600 mt-2 animate-pulse">Playing question...</p>}
          </>
        )}
      </div>

      <div className="w-full p-3 bg-blue-50 rounded-lg border border-blue-200 text-blue-800 font-medium text-center text-sm">
        <p>{interviewStatus}</p>
        {isRecording && <p className="text-sm mt-1">Time left: <span className="font-bold">{formatTime(timeLeft)}</span></p>}
        {isLoading && !isRecording && !isAudioPlaying && <p className="text-xs mt-1 animate-pulse">Processing...</p>}
      </div>

      {transcript && !isLoading && (
          <div className="w-full bg-green-50 p-3 rounded-lg border border-green-200 shadow-sm">
            <p className="text-green-800 font-semibold text-sm">Your last transcribed answer:</p>
            <p className="text-green-700 text-xs mt-1 italic">{(transcript.length > 150 ? transcript.substring(0, 147) + "..." : transcript)}</p>
          </div>
        )}

      <div className="flex flex-col sm:flex-row items-center justify-center w-full space-y-3 sm:space-y-0 sm:space-x-4 mt-4">
        <button
          onClick={() => handleStopAndSubmit(false, false)}
          disabled={!isRecording || isLoading}
          className={`flex items-center justify-center px-6 py-3 rounded-full shadow-lg transition-all duration-300 transform hover:scale-105
            bg-green-500 hover:bg-green-600 text-white
            disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          <StopIcon className="h-5 w-5 mr-2" /> Submit Answer
        </button>
        
        <button
          onClick={() => handleStopAndSubmit(false, true)}
          disabled={isLoading || interviewComplete}
          className="flex items-center justify-center px-6 py-3 rounded-full shadow-lg transition-all duration-300 transform hover:scale-105
            bg-red-500 hover:bg-red-600 text-white
            disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <HandRaisedIcon className="h-5 w-5 mr-2" /> End Interview
        </button>
      </div>
    </div>
  );
}

export default InterviewPanel;
