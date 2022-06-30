# cd Documents/git/a2ei_nigeria_grid_analysis/ ; streamlit run a2ei_grid_analysis.py

import streamlit as st
import psycopg2
from datetime import datetime, date, time , timedelta


# Page design configutration
st.set_page_config(
    page_title="st_dash_aam",
    page_icon=":sunny:",
    initial_sidebar_state="expanded",
    layout="wide",
)

# Sidebar elements
aam_id = str(st.sidebar.text_input('AAM ID', 943))  # Set System Name


db_select = st.sidebar.radio(
    "Choose your Database",
    ('postgres', 'aws', 'local'))


def init_connection():
    return psycopg2.connect(**st.secrets[db_select])


conn = init_connection()


# set today's date
today = datetime.today()

time_start = st.sidebar.date_input('Start', value=(datetime(2022, 3, 12)))
time_end = st.sidebar.date_input('End', today)


df_mppt = pd.read_sql(f'''  
                            SELECT 
                                time + interval '1 hour' AS time
                                ,pv_power
                                ,charging_output_voltage
                            FROM 
                                skgsp2_logs_mppt 
                            WHERE 
                                aam_id = {aam_id} AND
                                time between \'{rng[0]}\' and \'{rng[1]}\'
                            ORDER BY time 
                        ''' , conn)

df_mppt