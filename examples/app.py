import streamlit as st

st.title("Hallo, ich bin ein Streamlit-Dashboard")
name = st.text_input("Wie heißt du?")
if st.button("Sag Hallo"):
    st.write(f"Hallo, {name}!")
