# app/services/llm_service.py

import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import vertexai
from vertexai.language_models import TextGenerationModel
from app.config.settings import settings
import time
import re
from google.oauth2 import service_account
import os

logger = logging.getLogger(__name__)

class InterviewContext:
    """Class to maintain interview context and history"""
    def __init__(self, resume_data: Dict, job_description: Optional[str] = None,
                 company_info: Optional[Dict] = None):
        self.resume_data = resume_data
        self.job_description = job_description
        self.company_info = company_info or {}
        self.history = []
        self.current_phase = "introduction"
        self.scores = {
            "communication": 0,
            "technical": 0,
            "behavioral": 0,
            "overall": 0
        }
        self.feedback = []
        self.questions_asked = []

class LLMService:
    def __init__(self):
        """Initialize the LLM service with Vertex AI"""
        try:
            self._setup_google_auth()
            self.model = None
            self._initialize_model()
            self.max_retries = 3
            self.retry_delay = 2  # seconds
            
            # Load interview questions and prompts
            self.load_interview_templates()
        except Exception as e:
            logger.error(f"Failed to initialize LLM service: {str(e)}")
            raise

    def _setup_google_auth(self):
        """Set up Google Cloud authentication"""
        try:
            credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            
            if not credentials_path or not os.path.exists(credentials_path):
                raise ValueError(
                    "GOOGLE_APPLICATION_CREDENTIALS environment variable not set "
                    "or file does not exist"
                )

            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )

            # Initialize Vertex AI with project and credentials
            vertexai.init(
                project=settings.GOOGLE_CLOUD_PROJECT,
                credentials=credentials
            )
            
            logger.info("Google Cloud authentication successful")
            
        except Exception as e:
            logger.error(f"Google Cloud authentication failed: {str(e)}")
            raise

    def _initialize_model(self):
        """Initialize the Vertex AI model"""
        try:
            if not self.model:
                self.model = TextGenerationModel.from_pretrained("mistral-7b")
                logger.info("Vertex AI model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI model: {str(e)}")
            raise

    def load_interview_templates(self):
        """Load interview questions and prompts from templates"""
        self.interview_phases = {
            "introduction": {
                "system_prompt": """You are an experienced job interviewer. Start the interview with a 
                professional introduction. Be friendly but maintain professionalism. Introduce yourself 
                and the company. Ask the candidate how they are doing today.""",
                "duration": 2  # minutes
            },
            "background": {
                "system_prompt": """Review the candidate's background based on their resume. Ask relevant 
                questions about their experience and skills. Focus on their most recent and relevant 
                experience.""",
                "duration": 5
            },
            "technical": {
                "system_prompt": """Ask technical questions relevant to the position. Evaluate the 
                candidate's technical knowledge and problem-solving abilities. Adapt the difficulty based 
                on their responses.""",
                "duration": 15
            },
            "behavioral": {
                "system_prompt": """Ask behavioral questions to assess the candidate's soft skills, 
                teamwork, and past experiences. Use the STAR method to evaluate responses.""",
                "duration": 10
            },
            "closing": {
                "system_prompt": """Wrap up the interview professionally. Ask if the candidate has any 
                questions. Thank them for their time and explain the next steps.""",
                "duration": 3
            }
        }

    def _create_system_prompt(self, context: InterviewContext) -> str:
        """Create system prompt based on current context"""
        phase_prompt = self.interview_phases[context.current_phase]["system_prompt"]
        
        base_prompt = f"""
        You are conducting a job interview for {context.company_info.get('name', 'our company')}.
        Position: {context.resume_data.get('target_position', 'the position')}
        
        Current Phase: {context.current_phase}
        
        Instructions:
        1. Maintain a professional and friendly tone
        2. Ask one question at a time
        3. Provide brief feedback after each response
        4. Stay focused on the current interview phase
        5. Keep responses concise and clear
        
        {phase_prompt}
        """
        
        if context.job_description:
            base_prompt += f"\nJob Description: {context.job_description}"
            
        return base_prompt

    async def generate_response(self, 
                              context: InterviewContext, 
                              user_input: str) -> Dict:
        """Generate interviewer response based on context and user input"""
        try:
            if not self.model:
                raise ValueError("Model not initialized")

            system_prompt = self._create_system_prompt(context)
            
            # Prepare conversation history
            conversation = "\n".join([
                f"{'Interviewer' if i%2==0 else 'Candidate'}: {msg}"
                for i, msg in enumerate(context.history[-4:])  # Keep last 4 messages
            ])
            
            full_prompt = f"""
            {system_prompt}
            
            Previous Conversation:
            {conversation}
            
            Candidate: {user_input}
            
            Generate a response that includes:
            1. A brief evaluation of the candidate's last response (internal)
            2. The next interview question or response (external)
            3. Updated scores for relevant categories (internal)
            
            Format the response as JSON with the following structure:
            {{
                "evaluation": "brief evaluation of the response",
                "response": "next question or response to candidate",
                "scores": {{
                    "communication": "score 0-100",
                    "technical": "score 0-100",
                    "behavioral": "score 0-100"
                }},
                "phase": "current or next phase",
                "feedback": "specific feedback for this interaction"
            }}
            """
            
            # Generate response with retries
            for attempt in range(self.max_retries):
                try:
                    response = self.model.predict(
                        full_prompt,
                        temperature=0.7,
                        max_output_tokens=1024,
                        top_k=40,
                        top_p=0.8,
                    ).text
                    
                    # Parse JSON response
                    response_data = json.loads(response)
                    
                    # Update context
                    context.history.extend([user_input, response_data["response"]])
                    context.current_phase = response_data["phase"]
                    context.feedback.append(response_data["feedback"])
                    
                    # Update scores
                    for category, score in response_data["scores"].items():
                        context.scores[category] = max(
                            context.scores[category],
                            int(score)
                        )
                    
                    # Calculate overall score
                    context.scores["overall"] = sum(
                        score for category, score in context.scores.items()
                        if category != "overall"
                    ) / 3
                    
                    return response_data
                    
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        logger.error(f"Failed to generate response after {self.max_retries} attempts: {str(e)}")
                        raise
                    time.sleep(self.retry_delay)
                    
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return {
                "evaluation": "Error in processing response",
                "response": "I apologize, but I'm having trouble processing that. Could you please repeat your answer?",
                "scores": context.scores,
                "phase": context.current_phase,
                "feedback": "Technical difficulty in processing response"
            }

    def generate_final_report(self, context: InterviewContext) -> Dict:
        """Generate final interview report"""
        try:
            if not self.model:
                raise ValueError("Model not initialized")

            report_prompt = f"""
            Generate a comprehensive interview report based on the following information:
            
            Candidate Position: {context.resume_data.get('target_position')}
            Interview Duration: {len(context.history) // 2} interactions
            
            Scores:
            {json.dumps(context.scores, indent=2)}
            
            Feedback History:
            {json.dumps(context.feedback, indent=2)}
            
            Generate a report with the following sections:
            1. Executive Summary
            2. Strengths
            3. Areas for Improvement
            4. Detailed Feedback by Category
            5. Recommendations
            
            Format the response as JSON.
            """
            
            response = self.model.predict(
                report_prompt,
                temperature=0.7,
                max_output_tokens=2048,
            ).text
            
            report_data = json.loads(response)
            report_data["scores"] = context.scores
            report_data["timestamp"] = datetime.utcnow().isoformat()
            
            return report_data
            
        except Exception as e:
            logger.error(f"Error generating final report: {str(e)}")
            return {
                "error": "Failed to generate report",
                "scores": context.scores,
                "timestamp": datetime.utcnow().isoformat()
            }

    def extract_questions(self, text: str) -> List[str]:
        """Extract questions from text"""
        # Simple question extraction using regex
        questions = re.findall(r'[^.!?]*\?', text)
        return [q.strip() for q in questions if len(q.strip()) > 10]

    def is_available(self) -> bool:
        """Check if the LLM service is available"""
        return self.model is not None

# Usage example
if __name__ == "__main__":
    # Test LLM service
    llm_service = LLMService()
    
    # Test context
    test_context = InterviewContext(
        resume_data={
            "target_position": "Software Engineer",
            "experience": "5 years in Python development"
        },
        job_description="Looking for a senior Python developer with ML experience",
        company_info={"name": "Tech Corp"}
    )
    
    # Test response generation
    import asyncio
    
    async def test_interview():
        response = await llm_service.generate_response(
            test_context,
            "I have 5 years of experience in Python development."
        )
        print("Response:", json.dumps(response, indent=2))
        
        # Generate final report
        report = llm_service.generate_final_report(test_context)
        print("Final Report:", json.dumps(report, indent=2))
    
    asyncio.run(test_interview())