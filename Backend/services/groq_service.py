# groq_service.py
# UNIQUE IDENTIFIER FOR THIS FILE VERSION: groq_service_20250613_DirectTTSCall_EnhancedInterviewLogic_V2
import httpx
import base64
import json
from typing import Dict, List, Any, Optional
import time
import io
import sys
import inspect

from groq import Groq
from gtts import gTTS

# Placeholder for Groq API Key. This will be loaded from the config.
GROQ_API_KEY_PLACEHOLDER = ""

class GroqService:
    """
    Service class for interacting with the Groq API for LLM, STT, and TTS functionalities.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        # Initialize Groq client
        self.groq_client = Groq(api_key=self.api_key)

        print(f"--- DEBUG: Initializing GroqService. Groq client instance: {self.groq_client}")
        # print(f"--- DEBUG: sys.path (where Python looks for modules): {sys.path}")
        # print(f"--- DEBUG: Type of self.groq_client.audio: {type(self.groq_client.audio)}")
        # print(f"--- DEBUG: dir(self.groq_client.audio): {dir(self.groq_client.audio)}")
        # print(f"--- DEBUG: inspect.getmembers(self.groq_client.audio): {inspect.getmembers(self.groq_client.audio)}")


        self.llm_model_url = "https://api.groq.com/openai/v1/chat/completions"
        self.client = httpx.AsyncClient(timeout=120.0)


    async def _call_groq_llm_api(self, payload: Dict[str, Any], call_type: str) -> str:
        """
        Helper method to make a request to the Groq LLM API using httpx.
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

        print(f"--- Calling Groq LLM API for {call_type}...")
        try:
            response = await self.client.post(self.llm_model_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            print(f"--- Groq LLM API call for {call_type} successful.")

            if result.get("choices") and result["choices"][0].get("message") and \
               result["choices"][0]["message"].get("content"):
                return result["choices"][0]["message"]["content"]
            else:
                print(f"Unexpected Groq LLM API response structure for {call_type}: {result}")
                return json.dumps(result) # Return the full JSON if structure is not as expected
        except httpx.HTTPStatusError as e:
            print(f"HTTP error calling Groq LLM API for {call_type}: {e.response.status_code} - {e.response.text}")
            raise ConnectionError(f"Groq LLM API call failed with status {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            print(f"Request error calling Groq LLM API for {call_type}: {e}")
            raise ConnectionError(f"Network or request error during Groq LLM API call: {e}")
        except Exception as e:
            print(f"An unexpected error occurred during Groq LLM API call for {call_type}: {e}")
            raise

    async def generate_content(self, prompt: str) -> str:
        """Generates text content using Groq's LLM."""
        payload = {
            "model": "llama3-70b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 500,
        }
        return await self._call_groq_llm_api(payload, "generate_content")

    async def generate_structured_response(self, prompt: str) -> str:
        """Generates structured JSON response using Groq's LLM."""
        payload = {
            "model": "llama3-70b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 1500,
            "response_format": { "type": "json_object" }
        }
        return await self._call_groq_llm_api(payload, "generate_structured_response")

    async def generate_question(self, resume_info: Dict[str, Any], domain: str,
                                previous_questions: List[Dict[str, Any]]) -> str:
        """
        Generates an interview question using Groq's LLM based on resume, domain,
        interview stage (inferred from previous_questions count), and history.
        """
        resume_summary = f"""
        Candidate Name: {resume_info.get('name', 'N/A')}
        Experience: {resume_info.get('experience', 'N/A')}
        Skills: {', '.join(resume_info.get('skills', []))}
        Projects: {json.dumps(resume_info.get('projects', []))}
        Education: {resume_info.get('education', 'N/A')}
        """

        previous_q_texts = [q['text'] for q in previous_questions]
        previous_q_str = "\n".join(f"- {q}" for q in previous_q_texts) if previous_q_texts else "None"

        num_previous_questions = len(previous_questions)
        # The first question ("Tell me about yourself") is hardcoded in dakshy.py's start_interview.
        # So, num_previous_questions will be 1 when this function is called for the *second* actual interview question.

        question_type_description = ""
        prompt_instruction = ""
        question_type_tag = "generic" # Default tag

        # Determine if the domain is HR-like or technical-like
        # You can expand this list or make it more sophisticated
        hr_keywords = ["hr", "human resources", "recruitment", "managerial", "people management", "talent acquisition"]
        is_hr_domain = any(keyword in domain.lower() for keyword in hr_keywords)


        if num_previous_questions == 0:
            # This case is a fallback if the first question wasn't hardcoded.
            # For the current setup, start_interview handles the very first question.
            question_type_description = "a generic introductory question."
            prompt_instruction = "Ask a generic introductory question like 'Tell me about yourself?' or 'Walk me through your resume?'"
            question_type_tag = "generic_intro"

        elif num_previous_questions == 1: # This is for the 2nd question of the interview.
            question_type_description = "a follow-up question based on their resume (fact-based)."
            prompt_instruction = (
                "Based on the candidate's resume (their experience, a specific project, or a key skill), "
                "ask a specific, fact-finding follow-up question. This question should help to verify or elaborate on something concrete in their resume. "
                "Make it engaging and professional. Example: 'Your resume mentions project X. Can you elaborate on your specific role and contributions to that project?'"
            )
            question_type_tag = "resume_deep_dive"

        elif num_previous_questions == 2: # This is for the 3rd question of the interview.
            if is_hr_domain:
                question_type_description = "a foundational HR behavioral question."
                prompt_instruction = (
                    "Ask a common HR behavioral question. For example, 'Describe a challenging situation you faced at work and how you handled it,' "
                    "or 'What are your key strengths that you would bring to this role?' Focus on understanding their past behavior and character."
                )
                question_type_tag = "hr_behavioral_foundational"
            else: # Technical domains
                question_type_description = f"a foundational technical question for the {domain} domain."
                prompt_instruction = (
                    f"Ask a foundational technical question relevant to the candidate's skills and the {domain} role. "
                    "This could be a conceptual question about a core technology or methodology mentioned in their resume or common for the domain. "
                    "Avoid overly simple definitions; aim for assessing their understanding and ability to explain. Example: 'Can you explain the concept of [core_concept_from_resume_or_domain] and when you might use it?'"
                )
                question_type_tag = "technical_foundational"

        elif num_previous_questions == 3: # This is for the 4th question of the interview.
            if is_hr_domain:
                question_type_description = "a deeper HR behavioral or situational question."
                prompt_instruction = (
                    "Ask another HR behavioral question, perhaps focusing on weaknesses, learning from mistakes, teamwork, or conflict resolution. "
                    "For example, 'What do you consider your biggest professional weakness and how are you working to improve it?' "
                    "or 'Tell me about a time you had to work collaboratively on a difficult project and what your role was.'"
                )
                question_type_tag = "hr_behavioral_deep"
            else: # Technical domains
                question_type_description = f"a deeper dive technical or problem-solving question for the {domain} domain."
                prompt_instruction = (
                    f"Ask a more in-depth technical question or a practical problem-solving scenario related to the {domain} role or their resume. "
                    "This should probe their analytical skills or practical application of knowledge. "
                    "For instance, 'Imagine you are tasked with designing/optimizing [specific_system_related_to_domain], what are the key factors you would consider and what would be your approach?' or 'How would you troubleshoot [common_problem_in_domain]?'"
                )
                question_type_tag = "technical_problem_solving"

        elif num_previous_questions == 4: # This is for the 5th question of the interview (typically the last for a 5-q interview).
            if is_hr_domain:
                question_type_description = "a concluding HR question about motivation, fit, or expectations."
                prompt_instruction = (
                    "Ask a question related to career goals, motivation for the role, or company fit. "
                    "For example, 'Why are you interested in this particular role and our company?' or 'Where do you see yourself in 5 years?' "
                    "Optionally, if contextually appropriate for a final HR question and the role level, you could professionally inquire about salary: "
                    "'To ensure we are aligned, could you share your salary expectations for this type of role?' (Use this type of question carefully and only if it makes sense for the interview flow)."
                )
                question_type_tag = "hr_concluding"
            else: # Technical domains
                question_type_description = f"a final technical question, possibly more open-ended or scenario-based, for the {domain} domain."
                prompt_instruction = (
                    f"Ask a final technical question that could be more open-ended, forward-looking, or a slightly more complex problem/design consideration relevant to the {domain} role. "
                    "For example, 'How do you approach learning new technologies and advancements in the {domain} field?' or 'Describe a complex technical challenge you overcame in a past project, detailing your approach and the outcome.'"
                )
                question_type_tag = "technical_advanced"

        else: # Fallback for interviews longer than 5 questions.
            is_hr_domain = domain.lower() in ["hr", "human resources", "recruitment", "managerial", "non-technical"]
            if is_hr_domain:
                question_type_description = f"an advanced or situational question for the {domain} domain."
                prompt_instruction = (
                    "Ask an advanced situational judgment question, one about handling difficult workplace scenarios, or a question about their leadership/management style if applicable. "
                    "Ensure it's distinct from previous HR questions and probes a new dimension."
                )
                question_type_tag = "hr_advanced_situational"
            else: # Technical domains
                question_type_description = f"an advanced technical or system design question for the {domain} domain."
                prompt_instruction = (
                    f"Ask an advanced technical question, a system design question (if applicable to {domain}), or a question about best practices, architectural trade-offs, or future trends in the {domain} field. "
                    "This should challenge their depth of expertise."
                )
                question_type_tag = "technical_system_design"

        prompt = f"""
        You are a highly professional, insightful, and experienced AI Interviewer. Your current task is to conduct an interview for a {domain} role.
        Your goal is to assess the candidate thoroughly by asking a sequence of relevant and progressively challenging questions.

        Candidate's Summarized Resume Information:
        {resume_summary}

        Previous questions asked so far in this interview (avoid asking these or very similar ones again):
        {previous_q_str}

        You are now about to ask the {num_previous_questions + 1}th question in this interview.
        This question should be: {question_type_description}

        Specific instruction for generating THIS question:
        {prompt_instruction}

        General Guidelines for ALL questions you generate:
        1. Clarity and Conciseness: The question must be absolutely clear, concise, and unambiguous.
        2. Open-Ended: Frame questions to encourage detailed and thoughtful answers, not simple yes/no responses.
        3. Relevance: Ensure the question is highly relevant to the candidate's profile (resume), the {domain} domain, and the current stage of a professional interview.
        4. NO REPETITION: CRITICALLY IMPORTANT - DO NOT repeat any question from the "Previous questions asked so far" list, or a very close variation of it. Check carefully.
        5. Output Format: Generate ONLY the question text itself. Do NOT include any surrounding conversational text, preambles like "Okay, for your next question:", or any markdown/formatting. Just the raw question.
        6. Professional Tone: Maintain a consistently professional, respectful, and courteous tone throughout.
        7. Progression: Questions should generally progress in depth or type as the interview proceeds, following standard interview structures.
        """
        print(f"Prompting LLM for question (type: {question_type_tag}, stage {num_previous_questions + 1}): {prompt_instruction[:100]}...")
        generated_text = await self.generate_content(prompt)
        # The Question model in interview_models.py has a 'type' field.
        # We can return a dict or ensure the Question model is updated accordingly.
        # For now, just returning the text as per existing signature.
        # The 'type' of question can be added to the Question object in dakshy.py
        # using the question_type_tag defined above.
        return generated_text.strip() # Ensure no leading/trailing whitespace

    async def evaluate_answer(self, question: str, answer_transcript: str, resume_info: Dict[str, Any], domain: str) -> Dict[str, Any]:
        """Evaluates a candidate's answer using Groq's LLM."""
        resume_summary = f"""
        Candidate Name: {resume_info.get('name', 'N/A')}
        Experience: {resume_info.get('experience', 'N/A')}
        Skills: {', '.join(resume_info.get('skills', []))}
        Projects: {json.dumps(resume_info.get('projects', []))}
        Education: {resume_info.get('education', 'N/A')}
        """

        prompt = f"""
        You are an AI Interviewer evaluating an answer for a {domain} role.
        Here is the question asked: "{question}"
        Here is the candidate's transcribed answer: "{answer_transcript}"
        Here is the candidate's summarized resume information for context:
        {resume_summary}

        Please provide:
        1.  Detailed, constructive feedback on the answer. Consider:
            - Relevance to the question.
            - Clarity and conciseness of the response.
            - Depth of understanding and detail provided.
            - Technical accuracy (if applicable to the question and domain).
            - Use of examples or specific experiences.
            - Structure and coherence of the answer.
            - Professionalism in communication.
        2.  A score for this answer from 0.0 to 1.0, where 1.0 is an excellent, comprehensive, and accurate answer,
            and 0.0 is completely irrelevant, silent, or nonsensical.
            If the answer was effectively silent or extremely short due to a timeout or no input, assign a very low score (e.g., 0.0 to 0.2).

        Provide the output as a JSON object with the following keys:
        {{
            "feedback": "string (detailed, constructive feedback)",
            "score": "float (0.0 to 1.0, rounded to one decimal place)"
        }}
        """
        print(f"Prompting LLM for answer evaluation: {question[:50]}...")
        response_json_str = await self.generate_structured_response(prompt)
        try:
            # Clean the response string: remove markdown JSON block fences if present
            if response_json_str.startswith("```json"):
                response_json_str = response_json_str[len("```json"):]
            if response_json_str.endswith("```"):
                response_json_str = response_json_str[:-len("```")]
            response_json_str = response_json_str.strip()

            eval_data = json.loads(response_json_str)
            # Ensure score is a float and within bounds
            try:
                score = float(eval_data.get("score", 0.0))
            except (ValueError, TypeError):
                score = 0.0

            # Round score to one decimal place
            score = round(max(0.0, min(1.0, score)), 1)

            return {
                "feedback": eval_data.get("feedback", "No feedback generated or feedback was not in the expected format."),
                "score": score
            }
        except json.JSONDecodeError as e:
            print(f"Failed to parse answer evaluation JSON: {e} | Raw response: {response_json_str}")
            return {"feedback": f"Could not parse evaluation feedback from AI. Raw response: {response_json_str}", "score": 0.0}
        except Exception as e:
            print(f"Error in evaluate_answer processing: {e}")
            return {"feedback": f"An error occurred during evaluation processing: {e}", "score": 0.0}

    async def get_overall_evaluation(self, interview_history: List[Dict[str, Any]], resume_info: Dict[str, Any], domain: str) -> Dict[str, str]:
        """Generates an overall interview evaluation report using Groq's LLM."""
        history_str = ""
        total_score = 0.0
        num_answers = 0
        for i, entry in enumerate(interview_history):
            history_str += f"--- Question {i+1} ({entry.get('type', 'N/A')}) ---\n" # Added question type
            history_str += f"Q: {entry.get('question_text', 'N/A')}\n"
            history_str += f"A: {entry.get('answer_transcript', 'No answer')}\n"
            history_str += f"Feedback on A: {entry.get('feedback', 'No feedback')}\n"
            score_val = entry.get('score', 0.0)
            try:
                current_score = float(score_val)
            except (ValueError, TypeError):
                current_score = 0.0
            history_str += f"Score for A: {current_score:.1f}/1.0\n\n"
            total_score += current_score
            num_answers +=1

        average_score_str = f"{total_score / num_answers:.1f}/1.0" if num_answers > 0 else "N/A"


        resume_summary = f"""
        Candidate Name: {resume_info.get('name', 'N/A')}
        Experience: {resume_info.get('experience', 'N/A')}
        Skills: {', '.join(resume_info.get('skills', []))}
        Projects: {json.dumps(resume_info.get('projects', []))}
        Education: {resume_info.get('education', 'N/A')}
        """

        prompt = f"""
        You are an AI Interviewer tasked with providing a comprehensive overall evaluation for a candidate who has completed an interview for a {domain} role.
        Base your evaluation on their summarized resume and the detailed interview history provided below, including the types of questions asked.

        Candidate Resume Summary:
        {resume_summary}

        Interview History (Questions with types, Candidate's Answers, Feedback, Scores):
        {history_str}
        Average Score Across All Answers: {average_score_str}

        Please provide your final evaluation as a JSON object with three keys:
        1.  "overall_performance": A concise (2-4 sentences) summary of the candidate's performance.
            Consider their performance across different question types (e.g., resume-based, technical, behavioral).
            Highlight key strengths demonstrated and overall impression. Mention consistency if applicable.
        2.  "weak_points": Specific, actionable areas where the candidate struggled or could improve (2-3 bullet points).
            Focus on concrete examples from the interview history if possible (e.g., "clarity on [Specific Technical Topic from Q3]", "depth in [Skill from resume question Q2]").
            Be constructive and refer to question types if relevant (e.g., "Struggled with problem-solving questions").
        3.  "improvements": Concrete, actionable suggestions for how the candidate can improve in the identified weak points (2-3 bullet points).
            Suggest specific actions, resources, or practice methods if appropriate. Tailor suggestions to the types of questions where they underperformed.

        Example JSON Structure:
        {{
            "overall_performance": "The candidate demonstrated good foundational knowledge in [Area X] during technical questions and communicated their experiences clearly in response to resume-based questions. They showed [Positive Trait] when discussing [Specific Question/Topic]. Overall, a promising candidate with some areas for development, particularly in [area].",
            "weak_points": "- Lacked depth when discussing advanced [Specific Technical Topic from Q4 (technical_problem_solving)].\\n- Could provide more specific examples using the STAR method for behavioral questions (e.g., Q3 hr_behavioral_foundational).",
            "improvements": "- Recommend reviewing advanced concepts in [Specific Technical Topic] and practicing explaining them with real-world examples or case studies.\\n- Suggest preparing and practicing STAR method responses for common behavioral interview questions to add more structure and impact to answers."
        }}
        Ensure the output is valid JSON. For weak_points and improvements, use newline characters (\\n) to separate bullet points if you want them on new lines in the string.
        """
        print(f"Prompting LLM for overall evaluation...")
        response_json_str = await self.generate_structured_response(prompt)
        try:
            # Clean the response string: remove markdown JSON block fences if present
            if response_json_str.startswith("```json"):
                response_json_str = response_json_str[len("```json"):]
            if response_json_str.endswith("```"):
                response_json_str = response_json_str[:-len("```")]
            response_json_str = response_json_str.strip()

            eval_data = json.loads(response_json_str)
            return {
                "overall_performance": eval_data.get("overall_performance", "Error generating overall performance summary."),
                "weak_points": eval_data.get("weak_points", "Error generating list of weak points."),
                "improvements": eval_data.get("improvements", "Error generating improvement suggestions.")
            }
        except json.JSONDecodeError as e:
            print(f"Failed to parse overall evaluation JSON: {e} | Raw response: {response_json_str}")
            return {
                "overall_performance": f"Error parsing overall evaluation from AI. Raw response: {response_json_str}",
                "weak_points": "Could not parse.",
                "improvements": "Could not parse."
            }
        except Exception as e:
            print(f"Error in get_overall_evaluation processing: {e}")
            return {
                "overall_performance": f"An error occurred during overall evaluation processing: {e}",
                "weak_points": "Error.",
                "improvements": "Error."
            }

    async def text_to_speech(self, text: str) -> str:
        """
        Converts text to speech using gTTS.
        Returns base64 encoded audio.
        """
        print(f"--- Calling gTTS for text: '{text[:50]}...'")
        try:
            tts = gTTS(text=text, lang='en', slow=False)
            audio_buffer = io.BytesIO()
            # gTTS write_to_fp is synchronous, so no await needed here.
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0) # Rewind the buffer to the beginning
            audio_bytes = audio_buffer.read()
            print(f"--- gTTS call successful. Generated {len(audio_bytes)} bytes of audio.")
            return base64.b64encode(audio_bytes).decode('utf-8')
        except Exception as e:
            print(f"An error occurred during gTTS call: {e}")
            # Fallback to a dummy audio if gTTS fails
            dummy_mp3_base64 = "SUQzBAAAAAAAI1RTU1QAAAAAAAAAAAPkAAAAAAAAAAAAAAAAAAAAAAD/4xj/AQIAAAATc3RhbmRhcmQxAAAAAExhdmY1NC42My4xMDAAAAA///+7hAwAAAAAAAAAAAAAAADIzMDcBAwAAD0pVAACgQhQYAAAFFAAAAP//BIEAE0lTQUQgVkxYAAABAAACgSE4c+jRFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIYgAAAGoAAAEAACAFIAAAAACAAANsAAAABAAAAzAAAAB/Q/vLwL//jGP8BAgAAABNzdGFuZGFyZDEAAABMdmFmNTQuNjMuMTAwAAAAAAAAAAD///7uEDAAAAAAAAAAAAAAAADIzMDcBAwAAD0pVAACgQhQYAAAFFAAAAP//BIEAE0lTQUQgVkxYAAABAAACgSE4c+jRFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIYgAAAGoAAAEAACAFIAAAAACAAANsAAAABAAAAzAAAAB/Q/vLwL"
            print("--- Falling back to dummy TTS audio due to error. ---")
            return dummy_mp3_base64


    async def speech_to_text(self, audio_content: bytes) -> str:
        """
        Converts audio content to text using Groq's Whisper API.
        Expects audio_content as bytes.
        Uses the 'whisper-large-v3' model.
        """
        print(f"--- Calling Groq STT (Whisper) API for {len(audio_content)} bytes of audio...")

        try:
            # Create a file-like object from the bytes
            # Groq SDK expects a tuple: (filename, file_content_bytes, content_type)
            # For BytesIO, filename is often needed.
            audio_file_tuple = ("audio.webm", audio_content, "audio/webm")


            transcription = self.groq_client.audio.transcriptions.create(
                file=audio_file_tuple, # Pass the tuple here
                model="whisper-large-v3",
                # You can add more parameters like language if needed
                # language="en"
            )
            print(f"--- Groq STT API call successful. Transcription: '{transcription.text[:50]}...'")
            return transcription.text
        except Exception as e:
            print(f"Error calling Groq STT API: {e}")
            # Consider more specific error handling if Groq API returns structured errors
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                print(f"Groq API Error details: {e.response.text}")
            print("--- Falling back to simulated STT transcription due to error. ---")
            return "This is a simulated transcription of your speech due to an error with the STT service."

