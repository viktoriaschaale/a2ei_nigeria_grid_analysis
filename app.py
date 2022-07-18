#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# cd Documents/git/a2ei_nigeria_grid_analysis/ ; streamlit run app.py

from datetime import datetime
import streamlit as st
from helpers import fetch_cust, fetch_df, fetch_data_density


st.set_page_config(
    page_title="A2EI Grid Analysis",
    page_icon=":electric_plug:",
    initial_sidebar_state="expanded",
    layout="wide",
)

# SIDEBAR
st.sidebar.image("images/A2EI_horizontal_white_RGB.png",
                 use_column_width=True)
st.sidebar.text("")
st.sidebar.text("")

cust = fetch_cust()

cust

aam_id = st.sidebar.selectbox('AAM ID', cust.aam_id)
time_start = st.sidebar.date_input('Start', value=(datetime(2022, 3, 1)))
today = datetime.today()
time_end = st.sidebar.date_input('End', today)
rng = [time_start, time_end]

df = fetch_df(aam_id, rng)
df

data_density = fetch_data_density(aam_id)
data_density
