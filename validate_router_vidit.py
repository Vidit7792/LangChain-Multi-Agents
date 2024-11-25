
from fastapi import APIRouter, HTTPException
from langchain.schema import HumanMessage, AIMessage
from question_agent import QuestionGenerationAgent

# Initialize the FastAPI router and QuestionGenerationAgent instance
router = APIRouter()
question_agent = QuestionGenerationAgent()

@router.post("/generate_skill_based_question")
async def generate_skill_based_question(data: dict):
    """
    Endpoint to generate a skill-based multiple-choice question.

    Args:
        data (dict): Contains the "skill" for which the question is to be generated.

    Returns:
        dict: Generated question.
    """
    try:
        skill = data.get("skill")
        if not skill:
            raise HTTPException(status_code=400, detail="Skill is required")

        question = question_agent.generate_skill_based_question(skill)
        return {"question": question}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating question: {e}")


@router.post("/optimize_questions")
async def optimize_questions(data: dict):
    """
    Endpoint to generate multiple questions for a skill and return the best one.

    Args:
        data (dict): Contains the "skill" for which the questions are to be optimized.

    Returns:
        dict: Optimized question.
    """
    try:
        skill = data.get("skill")
        if not skill:
            raise HTTPException(status_code=400, detail="Skill is required")

        optimized_question = question_agent.optimize_questions(skill)
        return {"optimized_question": optimized_question}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error optimizing questions: {e}")


@router.post("/analyze_response")
async def analyze_response(data: dict):
    """
    Endpoint to analyze a user's response to a question.

    Args:
        data (dict): Contains the "question", "user_response", and "correct_answer".

    Returns:
        dict: Feedback on the user's response.
    """
    try:
        question = data.get("question")
        user_response = data.get("user_response")
        correct_answer = data.get("correct_answer")
        if not question or not user_response or not correct_answer:
            raise HTTPException(status_code=400, detail="Question, user response, and correct answer are required")

        is_correct, feedback = question_agent.analyze_response(question, user_response, correct_answer)
        return {"is_correct": is_correct, "feedback": feedback}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing response: {e}")


@router.post("/determine_next_action")
async def determine_next_action(data: dict):
    """
    Endpoint to determine the next best action in a conversation.

    Args:
        data (dict): Contains the "context" for determining the next action.

    Returns:
        dict: The determined next action.
    """
    try:
        context = data.get("context")
        if not context:
            raise HTTPException(status_code=400, detail="Context is required")

        next_action = question_agent.determine_next_action(context)
        return {"next_action": next_action}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error determining next action: {e}")


@router.get("/chat_history")
async def get_chat_history():
    """
    Endpoint to retrieve the chat history.

    Returns:
        dict: A list of messages in the chat history.
    """
    try:
        chat_history = question_agent.get_chat_history()
        return {"chat_history": [msg.content for msg in chat_history]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving chat history: {e}")


