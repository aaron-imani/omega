import streamlit as st
import pandas as pd

# Load the CSV file
df = pd.read_csv('sample.csv')

# Title of the app
st.title("Commit Message Comparison Survey")

# Introduction text
st.write("""
    This survey aims to gather practitioners' preferences for commit messages. 
    You will compare two commit messages (one generated by the state-of-the-art model (CMG) 
    and one generated by our model (AMG)) from four different perspectives.
""")

# Define the perspectives
perspectives = [
    "Clarity",
    "Conciseness",
    "Relevance",
    "Grammar and Spelling"
]

# Function to display a pair of commit messages and get user's preference
def compare_commit_messages(cmg, amg):
    st.write("### Commit Message 1 (CMG)")
    st.write(cmg)
    st.write("### Commit Message 2 (AMG)")
    st.write(amg)
    
    choices = ["CMG", "AMG"]
    preferences = {}
    for perspective in perspectives:
        st.write(f"#### {perspective}")
        preference = st.radio(f"Which commit message do you prefer for {perspective}?", choices, key=f"{cmg}-{amg}-{perspective}")
        preferences[perspective] = preference
    
    return preferences

# Initialize a dictionary to store survey results
survey_results = []

# Display commit messages and gather preferences
for index, row in df.iterrows():
    st.write(f"## Pair {index + 1}")
    preferences = compare_commit_messages(row['CMG'], row['AMG'])
    survey_results.append(preferences)

# Add a submit button
if st.button("Submit Survey"):
    # Save the survey results to a CSV file
    results_df = pd.DataFrame(survey_results)
    results_df.to_csv('survey_results.csv', index=False)
    st.write("Thank you for participating in the survey!")
    st.write("Your responses have been recorded.")

# To run the app, save this file and use the command: streamlit run survey.py
