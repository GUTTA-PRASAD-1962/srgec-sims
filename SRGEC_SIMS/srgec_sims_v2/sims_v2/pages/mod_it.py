"""pages/mod_it.py — IT module"""
import streamlit as st
from utils.auth import require_module_access
def show_module():
    require_module_access("IT")
    st.title("IT Infrastructure — IT-IIMS")
    st.info("The IT module is managed by the existing IT-IIMS system.")
    st.markdown("[Open IT-IIMS](http://localhost:8501)")
