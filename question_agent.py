from langchain.agents import Agent
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.memory import ConversationSummaryBufferMemory
from langchain.memory.chat_message_histories.in_memory import ChatMessageHistory

class QuestionGenerationAgent(Agent):
    def __init__(self):
        self.chat_model = ChatOpenAI()
        self.chat_history = ChatMessageHistory()
        self.memory = ConversationSummaryBufferMemory()

    def generate_skill_based_question(self, skill: str) -> str:
        """
        Generates a single multiple-choice question for a given skill.

        Args:
            skill (str): The skill for which the question will be generated.

        Returns:
            str: The generated multiple-choice question with options and the correct answer.
        """
        prompt = ChatPromptTemplate(
            system_message=SystemMessage(content="You are an AI designed to generate skill-based multiple-choice questions."),
            human_message=HumanMessage(content=f"Generate a multiple-choice question for the skill: {skill}")
        )
        # Assuming there's a method to generate the response
        response = self.chat_model.generate(prompt)
        return response