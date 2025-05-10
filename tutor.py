import streamlit as st
import google.generativeai as genai
import json
import random
from fractions import Fraction

# Configure Google Gemini API
API_KEY = "AIzaSyA-9-lTQTWdNM43YdOXMQwGKDy0SrMwo6c"  # Replace with your valid API key
genai.configure(api_key=API_KEY)
gemini_model = genai.GenerativeModel('gemini-1.5-flash')

class ProblemState:
    def __init__(self, problem: str, step: int, interface_elements: list, solution_steps: list):
        self.problem = problem
        self.step = step
        self.interface_elements = interface_elements
        self.solution_steps = solution_steps

    def to_json(self):
        return {
            "problem": self.problem,
            "current_step": self.step,
            "interface": self.interface_elements,
            "completed": self.is_done()
        }

    def is_done(self):
        return self.step >= len(self.solution_steps)

def generate_problem():
    """Generates a random fraction problem and its solution steps with explanations"""
    a = random.randint(1, 5)
    b = random.randint(1, 5)
    c = random.randint(1, 5)
    d = random.randint(1, 5)
    op = random.choice(["+", "-", "*", "/"])
    
    frac1 = Fraction(a, b)
    frac2 = Fraction(c, d)
    
    if op == "+":
        result = frac1 + frac2
        explanation = [
            f"Find common denominator: LCM of {b} and {d} is {result.denominator}",
            f"Convert fractions: {a}/{b} = {a*(result.denominator//b)}/{result.denominator}, " + 
            f"{c}/{d} = {c*(result.denominator//d)}/{result.denominator}",
            f"Add numerators: {a*(result.denominator//b)} + {c*(result.denominator//d)} = {result.numerator}"
        ]
    elif op == "-":
        result = frac1 - frac2
        explanation = [
            f"Find common denominator: LCM of {b} and {d} is {result.denominator}",
            f"Convert fractions: {a}/{b} = {a*(result.denominator//b)}/{result.denominator}, " + 
            f"{c}/{d} = {c*(result.denominator//d)}/{result.denominator}",
            f"Subtract numerators: {a*(result.denominator//b)} - {c*(result.denominator//d)} = {result.numerator}"
        ]
    elif op == "*":
        result = frac1 * frac2
        explanation = [
            f"Multiply numerators: {a} × {c} = {result.numerator}",
            f"Multiply denominators: {b} × {d} = {result.denominator}"
        ]
    else:  # division
        result = frac1 / frac2
        explanation = [
            f"Reciprocal of second fraction: {c}/{d} becomes {d}/{c}",
            f"Multiply fractions: {a}/{b} × {d}/{c} = {result.numerator}/{result.denominator}"
        ]
    
    problem_str = f"{a}/{b} {op} {c}/{d}"
    
    solution_steps = [
        {"sai": ("numerator", "UpdateTextField", str(result.numerator)), 
         "description": explanation[0]},
        {"sai": ("denominator", "UpdateTextField", str(result.denominator)), 
         "description": explanation[1] if len(explanation) >1 else "Enter denominator"},
        {"sai": ("submit", "PressButton", ""), "description": "Submit solution"}
    ]
    
    return problem_str, solution_steps, explanation

class MathTutor:
    def __init__(self, problem: str, solution_steps: list):
        self.problem = problem
        self.solution_steps = solution_steps
        self.current_step = 0
        self.interface = [
            {"id": "numerator", "type": "text", "label": "Numerator"},
            {"id": "denominator", "type": "text", "label": "Denominator"},
            {"id": "submit", "type": "button", "label": "Submit"}
        ]
        self._update_state()

    # ... (keep other MathTutor methods the same) ...

class GeminiTutor:
    def __init__(self):
        self.experience_buffer = []
    
    def generate_action(self, state: ProblemState, mode: str):
        prompt = self._build_prompt(state, mode)
        try:
            response = gemini_model.generate_content(prompt)
            return self._parse_response(response.text)
        except Exception as e:
            st.error(f"API Error: {str(e)}")
            return None, None

    def _build_prompt(self, state: ProblemState, mode: str):
        base = f"""Solve: {state.problem}
Current Step: {state.step + 1}/{len(state.solution_steps)}
Interface: {json.dumps(state.interface_elements, indent=2)}
        
Please explain the step-by-step process to solve this problem. Then provide the action in JSON format.
Example response:
First, find a common denominator by...
Then, add the numerators...
Finally, [\"denominator\", \"UpdateTextField\", \"6\"]"""
        
        return base

    def _parse_response(self, text: str):
        try:
            # Extract JSON part from response
            json_start = text.find('[')
            json_end = text.find(']') + 1
            json_str = text[json_start:json_end]
            
            explanation = text[:json_start].strip()
            action = tuple(json.loads(json_str))
            return action, explanation
        except Exception as e:
            return ("error", "parse_failed", str(e)), "Failed to parse response"

def main():
    st.set_page_config(page_title="Math Tutor", page_icon="🧮")
    
    if 'tutor' not in st.session_state:
        problem, steps, _ = generate_problem()
        st.session_state.tutor = MathTutor(problem, steps)
        st.session_state.agent = GeminiTutor()
        st.session_state.current_inputs = {"numerator": "", "denominator": ""}
        st.session_state.attempts = 0
        st.session_state.show_hint = False
        st.session_state.tutor_explanation = ""

    with st.sidebar:
        st.header("Settings")
        mode = st.selectbox("Mode", ["Student", "Tutor"])
        st.write("---")
        if st.button("Reset Problem"):
            problem, steps, _ = generate_problem()
            st.session_state.tutor = MathTutor(problem, steps)
            st.session_state.current_inputs = {"numerator": "", "denominator": ""}
            st.session_state.attempts = 0
            st.session_state.show_hint = False
            st.session_state.tutor_explanation = ""

    st.title("Fraction Arithmetic Tutor")
    st.markdown(f"**Problem:** {st.session_state.tutor.problem}")

    current_state = st.session_state.tutor.get_state()
    
    # Display interface
    col1, col2 = st.columns(2)
    with col1:
        numerator = st.text_input("Numerator", value=st.session_state.current_inputs["numerator"])
    with col2:
        denominator = st.text_input("Denominator", value=st.session_state.current_inputs["denominator"])
    
    if st.button("Submit Answer"):
        # ... (keep existing submit logic the same) ...

    if mode == "Tutor" and st.button("Show Tutor Answer"):
        action, explanation = st.session_state.agent.generate_action(current_state, "tutor")
        if action and action[0] in st.session_state.current_inputs:
            st.session_state.tutor_explanation = explanation
            st.session_state.current_inputs[action[0]] = action[2]
            st.experimental_rerun()
    
    if st.session_state.tutor_explanation:
        st.markdown("### Tutor's Explanation")
        st.write(st.session_state.tutor_explanation)
        st.write(f"**Correct Value:** {st.session_state.current_inputs['numerator']}/{st.session_state.current_inputs['denominator']}")

    # ... (keep remaining elements the same) ...

if __name__ == "__main__":
    main()
