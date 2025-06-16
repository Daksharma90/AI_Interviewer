# dakshy.py
print("--- LOADING MAIN.PY WITH UNIQUE ID: 20250613_Backend_Local_V1_FullAudio_FinalNoSpaces_EnhancedInterview ---")

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import json
import uuid
import base64

from config import settings
from services.resume_parser import parse_resume
from services.groq_service import GroqService
from models.interview_models import (
    ResumeInfo, Question, InterviewStartResponse, SubmitAnswerRequest, SubmitAnswerResponse,
    OverallEvaluation, GetNextQuestionRequest, GetQuestionResponse
)

app = FastAPI(
    title="AI Interviewer Backend",
    description="Backend API for managing AI-powered interviews.",
    version="0.2.0" # Version updated for new logic
)

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

groq_service = GroqService(api_key=settings.GROQ_API_KEY)

interview_sessions: Dict[str, Dict[str, Any]] = {}
questions_asked_history: Dict[str, List[Dict[str, Any]]] = {} # Stores {"id": str, "text": str, "type": str}
answers_history: Dict[str, List[Dict[str, Any]]] = {}


@app.post("/start-interview", response_model=InterviewStartResponse, summary="Upload resume and start interview")
async def start_interview(
    resume: UploadFile = File(..., description="The candidate's resume file (PDF or DOCX)."),
    domain: str = Form(..., description="The interview domain (e.g., 'HR', 'Engineering', 'Data Science').")
):
    try:
        session_id = str(uuid.uuid4())
        print(f"Starting new interview session: {session_id} for domain: {domain}")

        file_content = await resume.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="Uploaded resume file is empty.")

        parsed_resume_info = await parse_resume(file_content, resume.filename, groq_service)
        resume_info_model = ResumeInfo(**parsed_resume_info)
        print(f"Resume parsed successfully for session {session_id}: {resume_info_model.name}, Skills: {resume_info_model.skills[:5]}")

        candidate_name = resume_info_model.name if resume_info_model.name and resume_info_model.name.strip() else "Candidate"
        first_question_text = f"Hello {candidate_name}, thank you for joining. To start, could you please tell me a bit about yourself and walk me through your resume?"
        
        question_id = str(uuid.uuid4())
        # The type for the first question is 'generic_intro'
        first_question = Question(id=question_id, text=first_question_text, type="generic_intro")
        print(f"First question set for session {session_id}: {first_question.text}")

        question_audio_base64 = await groq_service.text_to_speech(first_question_text)
        print(f"Audio generated for first question for session {session_id}.")

        interview_sessions[session_id] = {
            "resume_info": resume_info_model,
            "domain": domain,
            "current_question": first_question, # Store the Question model
            "session_id": session_id,
            # "interview_stage" can be inferred from questions_asked_history length if needed
        }
        questions_asked_history[session_id] = [{"id": question_id, "text": first_question_text, "type": first_question.type}]
        answers_history[session_id] = []

        return JSONResponse(content={
            "question": first_question.dict(),
            "audio_base64": question_audio_base64,
            "resume_info": resume_info_model.dict(),
            "session_id": session_id
        })

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Bad Request: {str(e)}")
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=f"Service Unavailable: Problem communicating with external AI service. {str(e)}")
    except Exception as e:
        print(f"Error in /start-interview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error while starting interview: {str(e)}")


@app.post("/submit-answer", response_model=SubmitAnswerResponse, summary="Submit candidate's answer and get next question/evaluation")
async def submit_answer(
    session_id: str = Form(..., description="The unique ID of the current interview session."),
    question_id: str = Form(..., description="The ID of the question to which this answer corresponds."),
    is_timeout: bool = Form(..., description="True if the answer was due to a timeout (no speech detected or time ran out)."),
    force_end: bool = Form(False, description="True if the user explicitly ended the interview."),
    audio_file: Optional[UploadFile] = File(None, description="The candidate's audio recording of the answer (WebM format).")
    # Removed resume_info and domain from Form, will get from session
):
    """
    Receives candidate's answer (audio), transcribes it, evaluates it, 
    and then determines the next action: either generate the next question 
    or provide the final interview evaluation.
    """
    try:
        if session_id not in interview_sessions:
            raise HTTPException(status_code=404, detail=f"Interview session {session_id} not found.")

        session_data = interview_sessions[session_id]
        resume_info_model: ResumeInfo = session_data["resume_info"]
        domain_str: str = session_data["domain"]

        question_text = None
        question_type = "unknown" # Default type
        for q_entry in questions_asked_history.get(session_id, []):
            if q_entry["id"] == question_id:
                question_text = q_entry["text"]
                question_type = q_entry.get("type", "unknown") # Get type from history
                break
        if not question_text:
            raise HTTPException(status_code=404, detail=f"Question with ID {question_id} not found in session history for session {session_id}.")

        print(f"Received answer for session {session_id}, question ID {question_id} (type: {question_type}). Timeout: {is_timeout}, Force End: {force_end}")

        answer_transcript = "No answer provided (timeout)."
        if audio_file and audio_file.file:
            audio_content = await audio_file.read()
            if audio_content:
                answer_transcript = await groq_service.speech_to_text(audio_content)
                print(f"Transcribed answer for session {session_id}: '{answer_transcript}'")
            else:
                print(f"Warning: audio_file was provided but its content was empty for session {session_id}.")
        
        evaluation_result = await groq_service.evaluate_answer(
            question=question_text,
            answer_transcript=answer_transcript,
            resume_info=resume_info_model.dict(),
            domain=domain_str
        )
        print(f"Answer evaluation for session {session_id}: Feedback: {evaluation_result['feedback'][:50]}..., Score: {evaluation_result['score']}")

        answers_history[session_id].append({
            "question_id": question_id,
            "question_text": question_text,
            "question_type": question_type, # Store question type
            "answer_transcript": answer_transcript,
            "feedback": evaluation_result["feedback"],
            "score": evaluation_result["score"],
            "is_timeout": is_timeout
        })
        print(f"Session {session_id} current answers history length: {len(answers_history[session_id])}")

        current_answered_questions_count = len(answers_history[session_id])
        MAX_QUESTIONS_PER_INTERVIEW = 5 # This includes the initial "Tell me about yourself"

        if not force_end and current_answered_questions_count < MAX_QUESTIONS_PER_INTERVIEW:
            next_action = "next_question"
            print(f"Generating next question for session {session_id}. Question count: {current_answered_questions_count + 1}")

            # Determine question type tag based on number of previous questions
            num_prev_q = len(questions_asked_history.get(session_id, []))
            next_question_type_tag = "technical" # Default, will be refined by groq_service
            if num_prev_q == 1: next_question_type_tag = "resume_deep_dive"
            elif num_prev_q == 2:
                is_hr_domain = domain_str.lower() in ["hr", "human resources", "recruitment", "managerial", "non-technical"]
                next_question_type_tag = "hr_behavioral_foundational" if is_hr_domain else "technical_foundational"
            elif num_prev_q == 3:
                is_hr_domain = domain_str.lower() in ["hr", "human resources", "recruitment", "managerial", "non-technical"]
                next_question_type_tag = "hr_behavioral_deep" if is_hr_domain else "technical_problem_solving"
            elif num_prev_q == 4:
                is_hr_domain = domain_str.lower() in ["hr", "human resources", "recruitment", "managerial", "non-technical"]
                next_question_type_tag = "hr_concluding" if is_hr_domain else "technical_advanced"
            else: # Fallback for more questions
                is_hr_domain = domain_str.lower() in ["hr", "human resources", "recruitment", "managerial", "non-technical"]
                next_question_type_tag = "hr_advanced_situational" if is_hr_domain else "technical_system_design"


            next_question_text = await groq_service.generate_question(
                resume_info=resume_info_model.dict(),
                domain=domain_str,
                previous_questions=questions_asked_history[session_id] # Pass full history
            )
            next_question_id = str(uuid.uuid4())
            next_question = Question(id=next_question_id, text=next_question_text, type=next_question_type_tag)
            print(f"Next question (type: {next_question.type}) generated for session {session_id}: {next_question.text[:70]}...")

            next_question_audio_base64 = await groq_service.text_to_speech(next_question_text)
            print(f"Audio generated for next question for session {session_id}.")

            interview_sessions[session_id]["current_question"] = next_question
            questions_asked_history[session_id].append({"id": next_question_id, "text": next_question_text, "type": next_question.type})

            return JSONResponse(content={
                "transcript": answer_transcript,
                "feedback": evaluation_result["feedback"],
                "next_action": next_action,
                "question": next_question.dict(),
                "audio_base64": next_question_audio_base64,
                "message": "Answer processed. Here's your next question."
            })
        else:
            next_action = "end_interview"
            print(f"Interview completed for session {session_id}. Generating overall evaluation.")

            overall_evaluation_data = await groq_service.get_overall_evaluation(
                interview_history=answers_history[session_id], # Pass full answer history
                resume_info=resume_info_model.dict(),
                domain=domain_str
            )
            overall_evaluation_model = OverallEvaluation(**overall_evaluation_data)
            print(f"Overall evaluation generated for session {session_id}.")

            # Clean up session data
            if session_id in interview_sessions: del interview_sessions[session_id]
            if session_id in questions_asked_history: del questions_asked_history[session_id]
            if session_id in answers_history: del answers_history[session_id]
            print(f"Session {session_id} data cleaned up.")

            return JSONResponse(content={
                "transcript": answer_transcript,
                "feedback": evaluation_result["feedback"],
                "next_action": next_action,
                "overall_evaluation": overall_evaluation_model.dict(),
                "message": "Interview completed! Here is your performance report."
            })

    except HTTPException as e:
        # Log FastAPI's HTTPExceptions before re-raising
        print(f"HTTPException in /submit-answer for session {session_id}: {e.status_code} - {e.detail}")
        raise e
    except ConnectionError as e:
        # Log connection errors specifically
        print(f"ConnectionError in /submit-answer for session {session_id}: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Service Unavailable: Problem communicating with external AI service. {str(e)}")
    except json.JSONDecodeError as e:
        # Handle cases where resume_info might be malformed if it were still passed
        print(f"JSONDecodeError in /submit-answer for session {session_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON data provided: {str(e)}")
    except Exception as e:
        print(f"Unexpected error in /submit-answer for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error during answer submission: {str(e)}")


@app.post("/get-next-question", response_model=GetQuestionResponse, summary="Explicitly request the next question")
async def get_next_question_endpoint(request: GetNextQuestionRequest):
    """
    This endpoint allows the frontend to explicitly request the next question.
    It's particularly useful if the frontend's question timer expires before
    an answer is provided, or if the answer submission and next question
    retrieval are decoupled.
    It now fetches session-specific data (resume, domain) from the server.
    """
    session_id = request.session_id

    try:
        if session_id not in interview_sessions:
            raise HTTPException(status_code=404, detail=f"Interview session {session_id} not found.")

        session_data = interview_sessions[session_id]
        resume_info_model: ResumeInfo = session_data["resume_info"]
        domain_str: str = session_data["domain"]
        
        # Ensure answers_history and questions_asked_history are initialized for the session
        # This might be redundant if start_interview always initializes them, but good for safety
        if session_id not in answers_history:
            answers_history[session_id] = []
        if session_id not in questions_asked_history:
            # This state should ideally not happen if start_interview was called
            # but if it does, we might not have a first question.
            # For now, we'll rely on start_interview to set up the initial question.
             raise HTTPException(status_code=500, detail=f"Session {session_id} has no question history. Start interview first.")


        current_answered_questions_count = len(answers_history.get(session_id, []))
        MAX_QUESTIONS_PER_INTERVIEW = 5

        if current_answered_questions_count < MAX_QUESTIONS_PER_INTERVIEW:
            print(f"Explicitly generating next question for session {session_id}. Answered: {current_answered_questions_count}")

            # Determine question type tag based on number of previous questions
            num_prev_q = len(questions_asked_history.get(session_id, []))
            next_question_type_tag = "technical" # Default
            if num_prev_q == 1: next_question_type_tag = "resume_deep_dive"
            elif num_prev_q == 2:
                is_hr_domain = domain_str.lower() in ["hr", "human resources", "recruitment", "managerial", "non-technical"]
                next_question_type_tag = "hr_behavioral_foundational" if is_hr_domain else "technical_foundational"
            elif num_prev_q == 3:
                is_hr_domain = domain_str.lower() in ["hr", "human resources", "recruitment", "managerial", "non-technical"]
                next_question_type_tag = "hr_behavioral_deep" if is_hr_domain else "technical_problem_solving"
            elif num_prev_q == 4:
                is_hr_domain = domain_str.lower() in ["hr", "human resources", "recruitment", "managerial", "non-technical"]
                next_question_type_tag = "hr_concluding" if is_hr_domain else "technical_advanced"
            else: # Fallback for more questions
                is_hr_domain = domain_str.lower() in ["hr", "human resources", "recruitment", "managerial", "non-technical"]
                next_question_type_tag = "hr_advanced_situational" if is_hr_domain else "technical_system_design"

            next_question_text = await groq_service.generate_question(
                resume_info=resume_info_model.dict(),
                domain=domain_str,
                previous_questions=questions_asked_history.get(session_id, [])
            )
            next_question_id = str(uuid.uuid4())
            next_question = Question(id=next_question_id, text=next_question_text, type=next_question_type_tag)
            print(f"Next question (type: {next_question.type}) explicitly generated for session {session_id}: {next_question.text[:70]}...")


            next_question_audio_base64 = await groq_service.text_to_speech(next_question_text)

            interview_sessions[session_id]["current_question"] = next_question
            questions_asked_history[session_id].append({"id": next_question_id, "text": next_question_text, "type": next_question.type})

            return JSONResponse(content={
                "status": "success",
                "question": next_question.dict(),
                "audio_base64": next_question_audio_base64,
                "session_id": session_id
            })
        else:
            # This case means the interview should have ended.
            # We should generate the overall evaluation if it hasn't been done.
            print(f"Interview for session {session_id} already completed or at max questions. Answered: {current_answered_questions_count}. Returning evaluation.")
            
            # Check if evaluation already exists or needs to be generated
            # This part might need more robust state management if overall_evaluation can be generated multiple times
            # For now, assume we generate it if not already clearly "ended"
            
            overall_evaluation_data = await groq_service.get_overall_evaluation(
                interview_history=answers_history.get(session_id, []), # Use potentially empty list if no answers
                resume_info=resume_info_model.dict(),
                domain=domain_str
            )
            overall_evaluation_model = OverallEvaluation(**overall_evaluation_data)

            # Clean up session data as the interview is now considered complete
            if session_id in interview_sessions: del interview_sessions[session_id]
            if session_id in questions_asked_history: del questions_asked_history[session_id]
            if session_id in answers_history: del answers_history[session_id]
            print(f"Session {session_id} data cleaned up after explicit next question request at interview end.")

            return JSONResponse(content={
                "status": "completed",
                "overall_evaluation": overall_evaluation_model.dict(),
                "session_id": session_id,
                "message": "Interview has reached its maximum number of questions. Here is the final evaluation."
            })

    except HTTPException as e:
        print(f"HTTPException in /get-next-question for session {session_id}: {e.status_code} - {e.detail}")
        raise e
    except ConnectionError as e:
        print(f"ConnectionError in /get-next-question for session {session_id}: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Service Unavailable: Problem communicating with external AI service. {str(e)}")
    except Exception as e:
        print(f"Error in /get-next-question for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error while fetching next question: {str(e)}")


@app.get("/", summary="Root endpoint")
async def read_root():
    """Basic endpoint to check if the backend is running."""
    return {"message": "AI Interviewer Backend is running! Visit /docs for API documentation."}

# Debug print statement: THIS IS WHAT WE NEED TO SEE IN THE TERMINAL
print("\n--- Registered FastAPI Routes (from main.py) ---")
for route in app.routes:
    if hasattr(route, 'path') and hasattr(route, 'methods'):
        print(f"Path: {route.path}, Methods: {', '.join(route.methods) if route.methods else 'N/A'}")
print("--------------------------------------------------\n")
