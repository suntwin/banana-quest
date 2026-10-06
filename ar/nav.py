import streamlit as st

PAGES: dict = {}


def go(name: str):
    page = PAGES.get(name)
    if page is not None:
        st.switch_page(page)
