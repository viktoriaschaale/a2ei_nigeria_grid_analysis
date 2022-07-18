#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import create_engine
# from datetime import datetime
# import numpy as np
import pandas as pd
# from plotly_calplot import calplot
# import plotly.graph_objects as go
# from plotly.subplots import make_subplots
import streamlit as st


db = st.secrets["aws"]


@st.cache(allow_output_mutation=True)
def get_db_conn():
    engine = create_engine(
        f"{db['lang']}://{db['user']}:{db['password']}@{db['host']}/{db['dbname']}")
    return engine.connect()


@st.cache
def fetch_cust():
    with st.spinner('Loading Data...'):
        sql = '''SELECT
                                    aam_id,
                                    country,
                                    location,
                                    latitude,
                                    longitude,
                                    cust_type,
                                    bat_size,
                                    inv_size,
                                    mcu_version,
                                    installation_date,
                                    installation_comp
                                FROM
                                    skgs_customers'''
        cust = pd.read_sql(sql, con=get_db_conn())
    return cust


@st.cache
def data_prep(df):
    df = df.sort_values(by=['time'])
    df['time'] = pd.to_datetime(df['time'])
    df.set_index(df['time'], inplace=True)
    return df


@st.cache
def fetch_df(aam_id, rng):
    df = pd.read_sql(f'''       SELECT
                                    time + interval '1 hour' AS time
                                    ,input_voltage
                                    ,peak_voltage
                                    ,output_voltage
                                FROM
                                    skgsp2_logs
                                WHERE
                                    aam_id = {aam_id} AND
                                    time between \'{rng[0]}\' and \'{rng[1]}\'
                                ORDER BY time
                            ''', get_db_conn())
    return df


@st.cache
def fetch_data_density(aam_id):
    data_density = pd.read_sql(f'''       SELECT
                                    time + interval '1 hour' AS time
                                    ,input_voltage
                                    ,peak_voltage
                                FROM
                                    skgsp2_logs
                                WHERE
                                    aam_id = {aam_id} AND
                                    time between '2021-01-01' and '2022-12-01'
                                ORDER BY time
                            ''', get_db_conn())
    data_density = data_prep(data_density)
    return data_density
