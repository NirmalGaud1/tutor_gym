import streamlit as st
import google.generativeai as genai
import json
import random
import re
from fractions import Fraction

# Configure Google Gemini API
API_KEY = "AIzaSyA-9-lTQTWdNM43YdOXMQwGKDy0SrMwo6c"
genai.configure(api_key=API_KEY)
gemini_model = genai.GenerativeModel('gemini-1.5-flash')

class ProblemState:
    def __init__(self, problem: str, step: int, interface_elements: list, solution_steps: list):
        self.problem = problem
        self.step = step
        self.interface_elements = interface_elements
        self.solution_steps = solution_steps

    def is_done(self):
        return self.step >= len(self.solution_steps)

def generate_problem():
    a = random.randint(1, 5)
    b = random.randint(1, 5)
    c = random.randint(1, 5)
    d = random.randint(1, 5)
    op = random.choice(["+", "-", "*", "/"])
    
    frac1 = Fraction(a, b)
    frac2 = Fraction(c, d)
    
    if op in ["+", "-"]:
        result = frac1 + frac2 if op == "+" else frac1 - frac2
        lcm = result.denominator
        solution_steps = [
            {"sai": ("denominator", "UpdateTextField", str(lcm)), "description": "Enter common denominator"},
            {"sai": ("numerator", "UpdateTextField", str(result.numerator)), "description": "Enter calculated numerator"},
            {"sai": ("submit", "PressButton", ""), "description": "Submit final answer"}
        ]
    else:
        result = frac1 * frac2 if op == "*" else frac1 / frac2
        solution_steps = [
            {"sai": ("numerator", "UpdateTextField", str(result.numerator)), "description": "Enter numerator"},
            {"sai": ("denominator", "UpdateTextField", str(result.denominator)), "description": "Enter denominator"},
            {"sai": ("submit", "PressButton", ""), "description": "Submit final answer"}
        ]
    
    return f"{a}/{b} {op} {c}/{d}", solution_steps

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

    def get_current_step_action(self):
        return self.solution_steps[self.current_step]["sai"]

    def evaluate_action(self, action: tuple):
        expected = self.get_current_step_action()
        return action == expected

    def advance_step(self):
        self.current_step += 1

    def is_complete(self):
        return self.current_step >= len(self.solution_steps)

def main():
    st.set_page_config(page_title="Math Tutor", page_icon="🧮")
    
    if 'tutor' not in st.session_state:
        problem, steps = generate_problem()
        st.session_state.tutor = MathTutor(problem, steps)
        st.session_state.current_inputs = {"numerator": "", "denominator": ""}

    # Problem display
    st.markdown(f"**Problem:** {st.session_state.tutor.problem}")

    # Input fields
    current_step = st.session_state.tutor.current_step
    step_type = st.session_state.tutor.get_current_step_action()[0]

    col1, col2 = st.columns(2)
    with col1:
        numerator = st.text_input("Numerator", 
                                value=st.session_state.current_inputs["numerator"],
                                disabled=(current_step != 1 and st.session_state.tutor.solution_steps[0][0] != "numerator"))
    with col2:
        denominator = st.text_input("Denominator", 
                                  value=st.session_state.current_inputs["denominator"],
                                  disabled=(current_step != 0 and st.session_state.tutor.solution_steps[0][0] == "denominator"))

    # Submission logic
    if st.button("Submit Step"):
        current_action = (
            "numerator" if current_step == 1 else "denominator",
            "UpdateTextField",
            numerator if current_step == 1 else denominator
        ) if current_step < 2 else ("submit", "PressButton", "")

        if st.session_state.tutor.evaluate_action(current_action):
            st.session_state.tutor.advance_step()
            st.session_state.current_inputs = {"numerator": "", "denominator": ""}
            if st.session_state.tutor.is_complete():
                st.success("🎉 Correct! Problem solved!")
            else:
                st.success("✅ Correct! Proceed to next step")
        else:
            st.error("❌ Incorrect. Try again.")

    # Progress display
    st.markdown("---")
    st.write(f"**Step {current_step + 1} of {len(st.session_state.tutor.solution_steps)}**")
    st.progress((current_step + 1) / len(st.session_state.tutor.solution_steps))

if __name__ == "__main__":
    main()
