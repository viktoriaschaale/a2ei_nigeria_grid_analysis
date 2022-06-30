import streamlit as st
import psycopg2

#Page design configutration 
st.set_page_config(
     page_title="st_dash_aam",
     page_icon=":sunny:",
     initial_sidebar_state="expanded",
     layout="wide",
     )

##Sidebar elements
aam_id = str(st.sidebar.text_input('AAM ID', 943))  #Set System Name


db_select= st.sidebar.radio(
     "Choose your Database",
     ('postgres', 'aws','local'))


def init_connection():
    return psycopg2.connect(**st.secrets[db_select])


conn = init_connection()


#set today's date
today = datetime.today()

time_start=st.sidebar.date_input('Start',value=(datetime(2022, 3, 12)))
time_end=st.sidebar.date_input('End',today)
