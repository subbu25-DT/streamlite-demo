import streamlit as st
st.title(“Welcome to Streamlit”)
name = st.text_input(“Enter your name”)
if name: st.success(f “Hello {name}”)
age = st.slider(“Select your age”, 1, 100)
st.write(“Age:”, age)
if st.button(“Celebrate”): st.balloons()