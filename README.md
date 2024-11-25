Build module
In this module, the emphasis is on understanding as much as possible about the individuals’ skills. Relevant data is extracted from the resume and publicly available information like Linkedin and Github. The skills extracted can be a combination of technical as well as 21st century skills.
Validation Module
In this module, individuals can assess their knowledge on the skills extracted. Various challenges are thrown to the user by an AI BOT, which then assess the individual’s knowledge on the skills. The validation feature is unique in that:
●	It is totally crafted using AI.
●	It is adapted to an individual’s needs and abilities
●	It emphasizes on the importance of the inquiry process over finding the ‘right’ answer
●	It encourages participants to ask their own questions and cultivate curiosity
Grow Module
In this module, each individual will be pegged to potential job categories/job titles and career paths that s/he can explore. 
The right jobs are recommended to each individual by matching the skills he possesses with the job requirements. The skill gap is also identified for each individual for a particular job role and the best suited learning courses to bridge the gap.
Scope
The Validation module is a critical part of the product.  
The Validation module needs to be enhanced with the following features
1.	Update the AI BOT using Multi-Agent System (MAS) based architecture (using Langgraph). This includes personalized conversation flow, question generation as well as answer analyzer.
2.	Get the right mix of questions to be asked to be able to assess the individual on that skill with the minimal number of questions
3.	Improve the variety of questions asked. This includes question types like multiple choice questions, case studies, fill in the blanks, match the following, coding challenges among other to improve user experience.
Individual Activities

Area	Task	Description
Understanding	Product understanding including codes	Align team on objectives, deliverables, and timelines.
Design	Design Architecture	Design solution with best practices for implementing feature with Langgraph.
	Design Agent Interactions	Define how different agents will interact within the system, including roles for conversation flow, question generation, and answer analysis.
Development	Implement MAS Framework	Set up the MAS framework using Langgraph, ensuring agents are defined according to the design.
	Develop Conversation Router agent	Develop the conversational flow routing agent that will act as an orchestrator for the entire conversation flow
	Build Question Generation Agent + Tools	Develop the agent responsible for dynamic question generation, leveraging AI techniques.
This includes improving the variety of questions and also optimizing the questions so as to be able to assess user with minimal number of questions
	Build Answer Analysis Agent + Tools	Develop the agent for analyzing user responses, including feedback mechanisms.
	Build Next best action agent + Tools	Develop the NBA agent that will determine the next action (question, response etc) during the conversation
	Build Skill Atlas Agent + Tools	Develop an agent that can read the  skill atlas graph
	Build User Knowledge Graph Agent + Tools	Develop an agent that will keep the Personal Knowledge graph of the user updated
Integration & Testing	Integrate Agents with Existing System	Ensure all agents work seamlessly
	Internal Testing	Functional testing
	Integration testing	Integration and user testing
	Incorporate feedback	Review user feedback and identify areas for improvement in the implementation.
Deployment	Rollout	Deploy the updated AI BOT with the MAS architecture to all users.

