import streamlit as st
import google.generativeai as genai
import json
import time

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

    def _update_state(self):
        self.state = ProblemState(
            self.problem,
            self.current_step,
            self.interface,
            self.solution_steps
        )

    def get_state(self):
        return self.state

    def evaluate_action(self, element_id: str, action_type: str, value: str):
        if self.state.step < len(self.solution_steps):
            expected = self.solution_steps[self.state.step]["sai"]
            return (element_id == expected[0] and
                    action_type == expected[1] and
                    str(value).strip() == str(expected[2]).strip())
        return False

    def advance_step(self):
        self.current_step += 1
        self._update_state()

    def get_demonstration(self):
        if self.state.step < len(self.solution_steps):
            return self.solution_steps[self.state.step]["sai"]
        return None

    def is_complete(self):
        return self.current_step >= len(self.solution_steps)

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
            return None

    def _build_prompt(self, state: ProblemState, mode: str):
        base = f"""Solve: {state.problem}
Current Step: {state.step + 1}/{len(state.solution_steps)}
Interface: {json.dumps(state.interface_elements, indent=2)}"""

        if mode == "tutor":
            base += "\nGenerate the CORRECT next action as JSON [element, action, value]:"
        else:
            base += "\nGenerate a STUDENT'S action (might be wrong) as JSON:"

        return base + "\nResponse format: [\"element_id\", \"action_type\", \"value\"]"

    def _parse_response(self, text: str):
        try:
            text = text.strip().replace("```json\n", "").replace("\n```", "")
            return tuple(json.loads(text))
        except:
            return ("error", "parse_failed", text)

# Streamlit App
def main():
    st.set_page_config(page_title="Math Tutor", page_icon="🧮")

    if 'tutor' not in st.session_state:
        st.session_state.tutor = MathTutor(
            "1/2 + 1/3",
            [
                {"sai": ("numerator", "UpdateTextField", "5"), "description": "Enter the new numerator"},
                {"sai": ("denominator", "UpdateTextField", "6"), "description": "Enter the common denominator"},
                {"sai": ("submit", "PressButton", ""), "description": "Submit the result"}
            ]
        )
        st.session_state.agent = GeminiTutor()
        st.session_state.current_inputs = {"numerator": "", "denominator": ""}
        st.session_state.attempts = 0
        st.session_state.show_hint = False
        st.session_state.step_advanced = False

    with st.sidebar:
        st.header("Settings")
        mode = st.selectbox("Mode", ["Student", "Tutor"])
        st.write("---")
        if st.button("Reset Problem"):
            st.session_state.tutor = MathTutor(
                "1/2 + 1/3",
                [
                    {"sai": ("numerator", "UpdateTextField", "5"), "description": "Enter the new numerator"},
                    {"sai": ("denominator", "UpdateTextField", "6"), "description": "Enter the common denominator"},
                    {"sai": ("submit", "PressButton", ""), "description": "Submit the result"}
                ]
            )
            st.session_state.current_inputs = {"numerator": "", "denominator": ""}
            st.session_state.attempts = 0
            st.session_state.show_hint = False
            st.session_state.step_advanced = False

    st.title("Fraction Addition Tutor")
    st.markdown(f"**Problem:** {st.session_state.tutor.problem}")

    current_state = st.session_state.tutor.get_state()

    col1, col2 = st.columns(2)
    with col1:
        numerator = st.text_input("Numerator",
                                    value=st.session_state.current_inputs["numerator"],
                                    key="num_input")
        if numerator and current_state.step == 0 and st.session_state.tutor.evaluate_action("numerator", "UpdateTextField", numerator):
            st.session_state.current_inputs["numerator"] = numerator
            st.session_state.tutor.advance_step()
            st.session_state.step_advanced = True

    with col2:
        denominator = st.text_input("Denominator",
                                        value=st.session_state.current_inputs["denominator"],
                                        key="den_input")
        if denominator and current_state.step == 1 and st.session_state.tutor.evaluate_action("denominator", "UpdateTextField", denominator):
            st.session_state.current_inputs["denominator"] = denominator
            st.session_state.tutor.advance_step()
            st.session_state.step_advanced = True

    if st.button("Submit Answer"):
        if current_state.step == 2:
            action = ("submit", "PressButton", "")
            if st.session_state.tutor.evaluate_action(action[0], action[1], action[2]):
                st.session_state.tutor.advance_step()
                st.session_state.attempts = 0
                st.session_state.show_hint = False
                if st.session_state.tutor.is_complete():
                    st.success("🎉 Correct! Problem solved!")
                else:
                    st.success("✅ Correct! Move to next step")
            else:
                st.session_state.attempts += 1
                if st.session_state.attempts >= 2:
                    st.session_state.show_hint = True
                st.error("❌ Incorrect answer. Try again.")
        else:
            st.warning("Please enter the numerator and denominator before submitting.")

    if mode == "Tutor" and st.button("Show Tutor Answer"):
        action = st.session_state.agent.generate_action(current_state, "tutor")
        if action:
            st.write(f"**Tutor's Answer:** {action[2]}")
            st.session_state.current_inputs[action[0]] = action[2]
            if action[0] == "numerator" and current_state.step == 0:
                st.session_state.tutor.advance_step()
                st.session_state.step_advanced = True
            elif action[0] == "denominator" and current_state.step == 1:
                st.session_state.tutor.advance_step()
                st.session_state.step_advanced = True

    if st.session_state.show_hint:
        demo = st.session_state.tutor.get_demonstration()
        if demo and current_state.step < len(st.session_state.tutor.solution_steps):
            st.warning(f"💡 Hint: The correct value for {demo[0]} is {demo[2]}")

    st.write("---")
    st.subheader("Progress")
    st.write(f"Current Step: {current_state.step + 1}/{len(current_state.solution_steps)}")
    progress = (current_state.step + 1) / len(current_state.solution_steps)
    st.progress(progress)

    if st.session_state.step_advanced:
        st.session_state.step_advanced = False
        st.experimental_rerun()

if __name__ == "__main__":
    main()
