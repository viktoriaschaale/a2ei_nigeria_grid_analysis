# cd Documents/git/a2ei_nigeria_grid_analysis/ ; streamlit run a2ei_grid_analysis.py

import streamlit as st
import psycopg2
import pandas as pd 
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date, time , timedelta
from plotly.subplots import make_subplots


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
    ('aws','office'))


def init_connection():
    return psycopg2.connect(**st.secrets[db_select])


conn = init_connection()


# set today's date
today = datetime.today()

time_start = st.sidebar.date_input('Start', value=(datetime(2022, 3, 12)))
time_end = st.sidebar.date_input('End', today)

rng=[time_start,time_end]

df = pd.read_sql(f'''  
                            SELECT 
                                time + interval '1 hour' AS time
                                ,input_voltage
                                ,peak_voltage
                            FROM 
                                skgsp2_logs 
                            WHERE 
                                aam_id = {aam_id} AND
                                time between \'{rng[0]}\' and \'{rng[1]}\'
                            ORDER BY time 
                        ''' , conn)

df

#Data prep
df = df.sort_values(by = ['time'])
df['time'] = pd.to_datetime(df['time'])
df.set_index(df['time'],inplace=True)

#Plot 
final = make_subplots(specs=[[{"secondary_y": True}]])
final.add_trace(go.Scatter(x = df.index, y = df['input_voltage'], name =  'Input Voltage Inv (V)',  line_color = 'rgba(82, 82, 82, .8)'))         
final.add_trace(go.Scatter(x = df.index, y = df['peak_voltage'], name = 'Input Voltage MCU (V)',  line_color = 'rgb(245, 237, 111)'))
#final.add_trace(go.Scatter(x = dfnew.index, y = dfnew['battery_voltage'], name =  'Battery Voltage (V)', line_color = 'rgb(251, 117, 157)', line = dict(width = 3)), secondary_y = True)
#final.add_trace(go.Scatter(x = dfnew.index, y = dfnew['charging_output_voltage'], name =  'Battery Voltage mppt(V)', line_color = 'rgb(29, 100, 150)', line = dict(width = 3)), secondary_y = True)
final.update_layout(plot_bgcolor = 'white',
                    showlegend = False,
                    font = dict(size = 12),
                    width = 500,
                    height = 300,
                    title={
                            'text':  aam_id,
                            'y':0.9,
                            'x':0.5,
                            'xanchor': 'center',
                            'yanchor': 'top'})
final.update_xaxes( #dtick = 14,
                    tickformat='%d/%m',
                    ticks = 'outside', 
                    gridcolor = 'lightgrey', 
                    linecolor = 'lightgrey')

final.update_xaxes(title = "Hour of the Day",
                    row = 2, col = 1)

final.update_yaxes(title_text = 'Voltage (V)',
                    secondary_y = True, 
                    showline = True,
                    linewidth = 1,
                    linecolor = 'lightgrey',
                    # color = 'rgba(2251, 117, 157, 1)',
                    showticklabels = True,
                    ticks = 'outside',
                    range=[20,30]
                    )

final.update_yaxes(title_text = 'Power (W)',
                        showgrid = True,
                        secondary_y = False, 
                        showline = True,
                        linewidth = 1,
                        linecolor = 'lightgrey',
                        showticklabels = True,
                        gridcolor = 'lightgrey', 
                        ticks = 'outside',
                        range=[0,1000])

st.plotly_chart(final, use_container_width=True)

#-------------------------------------------