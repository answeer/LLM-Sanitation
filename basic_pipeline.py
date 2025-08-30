from llm_chat import test_llm  # Import the LLM query module
from dotenv import load_dotenv
import os
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO)

class ComplianceBulletinAgent:
    def __init__(self, updated_sections, model_name, endpoint, key):
        """
        Initializes the agent and accepts extracted changes.

        :param updated_sections: dict, contains changes categorized as "new", "advanced", "removed"
        :param model_name: string, LLM model name to query
        :param endpoint: string, the LLM endpoint URL
        :param key: string, the LLM API key
        """
        # Combine all changes into a single list while preserving the category
        self.all_changes = [
            f"{category.capitalize()}: {change}"
            for category, changes in updated_sections.items()
            for change in changes
        ]
        self.model_name = model_name
        self.endpoint = endpoint
        self.key = key

    def identify_responsible_team_with_llm(self, changes):
        """
        Use LLM to identify the responsible team for the given changes.

        :param changes: string, combined change descriptions from the bulletin
        :return: string, name of the responsible team
        """
        prompt = f"""
        Given the following changes:
        {changes}
        Identify the responsible team from the following teams:
        1. Fraud & Risk Management Team
        2. Dispute & Chargeback Operations Team
        3. Compliance & Regulatory Affairs
        4. IT & Technology / Core Banking Systems
        5. Payments Operations / Transaction Processing
        6. Interchange & Fees / Finance Team
        7. Merchant Acquiring / Partnerships
        8. Card Product & Business Team
        9. Information Security / Cybersecurity
        10. Legal Department
        11. Customer Service / Contact Center
        12. Audit & Risk Oversight
        Please return only the name of the responsible team.
        """
        try:
            team = test_llm(self.model_name, prompt, self.endpoint, self.key)
            return team.strip() if team else "Unknown Team"
        except Exception as e:
            logging.error(f"Error querying LLM: {e}")
            return "Unknown Team"

    def create_task_with_llm(self, changes, responsible_team):
        """
        Use LLM to create a task based on the changes and assign it to the responsible team.

        :param changes: string, combined change descriptions from the bulletin
        :param responsible_team: string, the team identified to be responsible
        :return: string, the generated task description
        """
        prompt = f"""
        Create a task for the following changes: '{changes}'. The task should include:
        - High-level task description
        - Definition of Ready
        - Definition of Done
        Assign this task to the '{responsible_team}' team.
        """
        try:
            task = test_llm(self.model_name, prompt, self.endpoint, self.key)
            return task.strip() if task else "Failed to generate task"
        except Exception as e:
            logging.error(f"Error querying LLM for task creation: {e}")
            return "Failed to generate task"

    def process_bulletin(self):
        """
        Processes the bulletin, generates tasks, and identifies responsible teams.

        :return: list, list of tasks generated
        """
        tasks = []
        
        # Combine all changes into one string
        changes_str = "\n".join(self.all_changes)
        
        # Identify the responsible team
        team = self.identify_responsible_team_with_llm(changes_str)

        # Create the task based on the changes and responsible team
        task = self.create_task_with_llm(changes_str, team)
        tasks.append({
            'changes': changes_str,
            'task': task,
            'responsible_team': team  # Record the responsible team
        })

        # Output results
        logging.info(f"Responsible Team: {team}")
        logging.info("\nGenerated Task:")
        for task in tasks:
            logging.info(f"Changes: {task['changes']}")
            logging.info(f"Task: {task['task']}")

        return tasks


# Example: Changes extracted from a compliance bulletin
updated_sections = {
    "new": [
        "Contactless biometric rule, reduced dispute response time."
    ],
    "advanced": [
        "Subscription cancellation requirement from advisory → mandatory."
    ],
    "removed": [
        "Reason code 4530 is no longer valid."
    ]
}

# LLM configuration
model_name = "claude-3-7-sonnet"
endpoint = os.getenv("ai_gateway")  # Make sure to set the correct endpoint
key = os.getenv("hackathon_key")    # Make sure to set the correct API key

# Initialize agent and process the bulletin
agent = ComplianceBulletinAgent(updated_sections, model_name, endpoint, key)
tasks = agent.process_bulletin()
