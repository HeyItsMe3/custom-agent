import os 
import yaml
import json
from termcolor import colored
from prompts import planning_agent_prompt, integration_agent_prompt
from search import WebSearcher
from groq import Groq
import requests
from dotenv import load_dotenv
load_dotenv()

""" def load_config(file_path):
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
        for key, value in config.items():
            os.environ[key] = value """

class Agent:
    def __init__(self, model, tool, temperature=0, max_tokens=1000, planning_agent_prompt=None, integration_agent_prompt=None, verbose=False):
        #load_config('config.yaml')
        self.client = Groq()
        #self.api_key = os.getenv('GROQ_API_KEY')
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.tool = tool
        self.tool_specs = tool.__doc__
        self.planning_agent_prompt = planning_agent_prompt
        self.integration_agent_prompt = integration_agent_prompt
        self.model = model
        self.verbose = verbose
    
    def run_planning_agent(self, query, plan=None, outputs=None, feedback=None):

        system_prompt = self.planning_agent_prompt.format(
            outputs=outputs,
            plan=plan,
            feedback=feedback,
            tool_specs=self.tool_specs
        )

        response = self.client.chat.completions.create(
             messages= [{"role": "user", "content": query},
                        {"role": "system", "content": system_prompt}],
            temperature= 0.3,
            model= "llama3-8b-8192",
            max_tokens= 1024)

        content = response.choices[0].message.content

        print(colored(f"Planning Agent: {content}", 'green'))

        return content
    
    def run_integration_agent(self, query, plan, outputs):
        system_prompt = self.integration_agent_prompt.format(
            outputs=outputs,
            plan=plan
        )

        response = self.client.chat.completions.create(
             messages= [{"role": "user", "content": query},
                        {"role": "system", "content": system_prompt}],
            temperature= 0.3,
            model= "llama3-8b-8192",
            max_tokens= 8192)

        content = response.choices[0].message.content   
        print(colored(f"Integration Agent: {content}", 'blue'))
        # print("Integration Agent:", content)

        return content
    
    def response_checker(self, response, query):
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "respose_checker",
                    "description": "Checck if the response meets the requirements",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "meets_requirements": {
                                "type": "string",
                                "description": """Check if the response meets the requirements of the query based on the following:
                                1. The response should be relevant to the query.
                                2. The response should be coherent and well-structured with citations.
                                3. The response should be comprehensive and address the query in its entirety.
                                4. The response must have answer to the question 
                                Return 'yes' if the response meets the requirements and 'no' otherwise.
                                """
                            },
                        },
                        "required": ["meets_requirements"]
                    }
                }
            }
        ]

        chat_response = self.client.chat.completions.create(
            model=self.model,
            messages = [{"role": "user", "content": f"Response: {response} \n Query: {query}"}],
            temperature=0,
            tools=tools,
            tool_choice="auto",
            max_tokens=8192
        )

        tool_calls = chat_response.choices[0].message.tool_calls[0]
        functions_args = json.loads(tool_calls.function.arguments)
        response = functions_args["meets_requirements"]

        if response == 'yes':
            return True
        else:
            return False

         
    def execute(self, iterations=5):
        query = input("Enter your query: ")
        tool =  self.tool(model=self.model, verbose=self.verbose)
        meets_requirements = False
        plan = None
        outputs = None
        response = None
        iterations = 0

        while not meets_requirements and iterations < 5:
            iterations += 1  
            plan = self.run_planning_agent(query, plan=plan, outputs=outputs, feedback=response)
            outputs = tool.use_tool(plan=plan, query=query)
            response = self.run_integration_agent(query, plan, outputs)
            meets_requirements = self.response_checker(response, query)

        print(colored(f"Final Response: {response}", 'cyan'))
        print(colored(f"Total iterations: {iterations}", "light_red"))
        
if __name__ == '__main__':
    agent = Agent(model="llama3-8b-8192",
                  tool=WebSearcher, 
                  planning_agent_prompt=planning_agent_prompt, 
                  integration_agent_prompt=integration_agent_prompt,
                  verbose=True
                  )
    agent.execute()


    

#what is cut off for bar exam in india in 2024 according to bar council of india?