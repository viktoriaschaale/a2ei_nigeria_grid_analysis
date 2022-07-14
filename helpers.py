#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy.engine import create_engine
from datetime import datetime
import numpy as np
import pandas as pd
from plotly_calplot import calplot
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st


@st.cache
def data_prep(df):
    df = df.sort_values(by=['time'])
    df['time'] = pd.to_datetime(df['time'])
    df.set_index(df['time'], inplace=True)
    return df
