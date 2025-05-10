import streamlit as st
import google.generativeai as genai
import json
import random
import re
from fractions import Fraction
import math

API_KEY = "AIzaSyA-9-lTQTWdNM43YdOXMQwGKDy0SrMwo6c"
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
    """Generates a random fraction problem with correct solution steps"""
    a = random.randint(1, 5)
    b = random.randint(1, 5)
    c = random.randint(1, 5)
    d = random.randint(1, 5)
    op = random.choice(["+", "-", "*", "/"])
    
    frac1 = Fraction(a, b)
    frac2 = Fraction(c, d)
    
    # Simplify result and handle negative fractions
    if op == "+":
        result = frac1 + frac2
        explanation = [
            f"Find common denominator: LCM of {b} and {d} is {result.denominator}",
            f"Convert fractions: {a}/{b} = {a*(result.denominator//b)}/{result.denominator}, " +
            f"{c}/{d} = {c*(result.denominator//d)}/{result.denominator}",
            f"Add numerators: {a*(result.denominator//b)} + {c*(result.denominator//d)} = {result.numerator}"
        ]
        solution_steps = [
            {"sai": ("denominator", "UpdateTextField", str(result.denominator)), "description": explanation[0]},
            {"sai": ("numerator", "UpdateTextField", str(result.numerator)), "description": explanation[2]},
            {"sai": ("submit", "PressButton", ""), "description": "Submit solution"}
        ]
    elif op == "-":
        result = frac1 - frac2
        explanation = [
            f"Find common denominator: LCM of {b} and {d} is {result.denominator}",
            f"Convert fractions: {a}/{b} = {a*(result.denominator//b)}/{result.denominator}, " +
            f"{c}/{d} = {c*(result.denominator//d)}/{result.denominator}",
            f"Subtract numerators: {a*(result.denominator//b)} - {c*(result.denominator//d)} = {result.numerator}"
        ]
        solution_steps = [
            {"sai": ("denominator", "UpdateTextField", str(abs(result.denominator))), "description": explanation[0]},
            {"sai": ("numerator", "UpdateTextField", str(result.numerator)), "description": explanation[2]},
            {"sai": ("submit", "PressButton", ""), "description": "Submit solution"}
        ]
    elif op == "*":
        result = frac1 * frac2
        explanation = [
            f"Multiply numerators: {a} × {c} = {result.numerator}",
            f"Multiply denominators: {b} × {d} = {result.denominator}"
        ]
        solution_steps = [
            {"sai": ("numerator", "UpdateTextField", str(result.numerator)), "description": explanation[0]},
            {"sai": ("denominator", "UpdateTextField", str(result.denominator)), "description": explanation[1]},
            {"sai": ("submit", "PressButton", ""), "description": "Submit solution"}
        ]
    else:  # division
        result = frac1 / frac2
        explanation = [
            f"Reciprocal of second fraction: {c}/{d} becomes {d}/{c}",
            f"Multiply fractions: ({a}/{b}) × ({d}/{c}) = {result.numerator}/{result.denominator}"
        ]
        solution_steps = [
            {"sai": ("numerator", "UpdateTextField", str(result.numerator)), "description": explanation[1]},
            {"sai": ("denominator", "UpdateTextField", str(abs(result.denominator))), "description": "Enter denominator"},
            {"sai": ("submit", "PressButton", ""), "description": "Submit solution"}
        ]
    
    # Simplify the result if needed
    result = result.limit_denominator()
    problem_str = f"{a}/{b} {op} {c}/{d}"
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
        self.state = ProblemState(self.problem, self.current_step, self.interface, self.solution_steps)

    def get_state(self):
        return self.state

    def evaluate_action(self, action: tuple):
        expected = self.solution_steps[self.state.step]["sai"]
        return (action[0] == expected[0] and 
                action[1] == expected[1] and 
                str(action[2]).strip() == str(expected[2]).strip())

    def advance_step(self):
        self.current_step += 1
        self.state = ProblemState(self.problem, self.current_step, self.interface, self.solution_steps)

    def get_demonstration(self):
        if self.state.step < len(self.solution_steps):
            return self.solution_steps[self.state.step]["sai"]
        return None

    def is_complete(self):
        return self.current_step >= len(self.solution_steps)

class GeminiTutor:
    def __init__(self):
        pass  # Removed unused experience_buffer

    def generate_action(self, state: ProblemState):
        prompt = self._build_prompt(state)
        try:
            response = gemini_model.generate_content(prompt)
            return self._parse_response(response.text)
        except Exception as e:
            st.error(f"API Error: {str(e)}. Please try again or generate a new problem.")
            return None, "Error generating response"

    def _build_prompt(self, state: ProblemState):
        current_step = state.solution_steps[state.step]
        return f"""Solve: {state.problem}
Current Step: {state.step + 1} of {len(state.solution_steps)} ({current_step['description']})
        
Explain the current step in detail, then provide the exact action in JSON format.
Required format: [element_id, action_type, value]

Example for denominator step:
1. Find the least common denominator...
2. The correct denominator is 6
["denominator", "UpdateTextField", "6"]"""

    def _parse_response(self, text: str):
        try:
            # Find the last JSON array in the response
            json_matches = re.findall(r'\[.*?\]', text)
            if not json_matches:
                return None, "No valid action found"
            
            json_str = json_matches[-1]  # Use the last match
            action = tuple(json.loads(json_str))
            explanation = text[:text.rfind(json_str)].strip()
            return action, explanation
        except Exception as e:
            return None, f"Parse error: {str(e)}"

def main():
    st.set_page_config(page_title="Math Tutor", page_icon="🧮")
    
    # Initialize session state
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
        if st.button("New Problem"):
            # Reset all relevant session state
            problem, steps, _ = generate_problem()
            st.session_state.tutor = MathTutor(problem, steps)
            st.session_state.agent = GeminiTutor()
            st.session_state.current_inputs = {"numerator": "", "denominator": ""}
            st.session_state.attempts = 0
            st.session_state.show_hint = False
            st.session_state.tutor_explanation = ""
            st.rerun()

    st.title("Fraction Calculator Tutor")
    current государ: ProblemState = st.session_state.tutor.get_state()
    st.markdown(f"**Problem:** {current_state.problem}")

    # Input fields
    col1, col2 = st.columns(2)
    with col1:
        numerator = st.text_input("Numerator", value=st.session_state.current_inputs["numerator"], key="num")
    with col2:
        denominator = st.text_input("Denominator", value=st.session_state.current_inputs["denominator"], key="den")

    if st.button("Submit"):
        st.session_state.current_inputs["numerator"] = numerator
        st.session_state.current_inputs["denominator"] = denominator

        expected = current_state.solution_steps[current_state.step]["sai"]
        action = (
            expected[0],  # element_id
            expected[1],  # action_type
            numerator if expected[0] == "numerator" else denominator
        )

        if st.session_state.tutor.evaluate_action(action):
            st.session_state.tutor.advance_step()
            st.session_state.attempts = 0
            st.session_state.show_hint = False
            if st.session_state.tutor.is_complete():
                st.success("🎉 Correct! Problem solved!")
            else:
                st.success("✅ Correct! Next step")
        else:
            st.session_state.attempts += 1
            if st.session_state.attempts >= 2:
                st.session_state.show_hint = True
            st.error("❌ Incorrect. Try again.")

    # Tutor answer section
    if mode == "Tutor":
        if st.button("Show Tutor Solution"):
            action, explanation = st.session_state.agent.generate_action(current_state)
            if action and action[0] in ["numerator", "denominator"]:
                st.session_state.current_inputs[action[0]] = action[2]
                st.session_state.tutor_explanation = explanation
                st.rerun()

        if st.session_state.tutor_explanation:
            st.markdown("### Step Explanation")
            st.write(st.session_state.tutor_explanation)
            st.markdown(f"**Current Step Answer:**")
            st.code(f"{st.session_state.current_inputs['numerator']}/{st.session_state.current_inputs['denominator']}")

    # Progress tracking
    st.markdown("---")
    st.subheader("Progress")
    if current_state.is_done():
        st.write("Problem Complete!")
        st.progress(1.0)
    else:
        st.write(f"Step {current_state.step + 1} of {len(current_state.solution_steps)}")
        st.progress(current_state.step / len(current_state.solution_steps))

if __name__ == "__main__":
    main()
