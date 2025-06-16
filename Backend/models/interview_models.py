from pydantic import BaseModel
from typing import Dict, List, Optional, Any

# Pydantic model for parsed resume information
class ResumeInfo(BaseModel):
    name: Optional[str] = "Candidate"
    email: Optional[str] = None
    phone: Optional[str] = None
    experience: Optional[str] = "No experience mentioned."
    skills: List[str] = []
    projects: List[Dict[str, str]] = []
    education: Optional[str] = None
    raw_text: str

# Pydantic model for an interview question
class Question(BaseModel):
    id: str
    text: str
    type: str # e.g., "generic", "resume_deep_dive", "technical_foundational", "hr_behavioral", etc.

# Pydantic model for an individual answer evaluation
class AnswerEvaluation(BaseModel):
    question_id: str
    transcript: str
    feedback: str
    score: float
    is_timeout: bool = False

# Pydantic model for the overall interview evaluation report
class OverallEvaluation(BaseModel):
    overall_performance: str
    weak_points: str
    improvements: str

# Request model for the /start-interview endpoint
class StartInterviewRequest(BaseModel):
    domain: str

# Response model for starting the interview / getting first question
class InterviewStartResponse(BaseModel):
    question: Question
    audio_base64: str
    resume_info: ResumeInfo
    session_id: str

# Request model for submitting an answer to the backend
class SubmitAnswerRequest(BaseModel):
    question_id: str
    is_timeout: bool # True if the answer was due to a timeout
    force_end: Optional[bool] = False # New flag to indicate early termination
    # session_id will be passed as a Form parameter directly in the endpoint

# Response model after submitting an answer
class SubmitAnswerResponse(BaseModel):
    transcript: str
    feedback: str
    next_action: str
    overall_evaluation: Optional[OverallEvaluation] = None
    question: Optional[Question] = None
    audio_base64: Optional[str] = None
    message: Optional[str] = None

# Request model for explicitly getting the next question
class GetNextQuestionRequest(BaseModel):
    session_id: str

# Response model for explicitly getting a question (first or next)
class GetQuestionResponse(BaseModel):
    status: str
    question: Optional[Question] = None
    audio_base64: Optional[str] = None
    overall_evaluation: Optional[OverallEvaluation] = None
    session_id: Optional[str] = None
