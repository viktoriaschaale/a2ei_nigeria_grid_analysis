# cd Documents/git/a2ei_nigeria_grid_analysis/ ; streamlit run a2ei_grid_analysis.py

import streamlit as st
import psycopg2
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date, time, timedelta
from plotly.subplots import make_subplots
import numpy as np


# Page design configutration
st.set_page_config(
    page_title="A2EI Grid Analysis",
    page_icon=":sunny:",
    initial_sidebar_state="expanded",
    layout="wide",
)

# st.markdown("<h1 style='text-align: center; color: rgb(223,116,149);'>A2EI Grid Analysis Tool</h1>",
#             unsafe_allow_html=True)

# SIDEBAR
# logo
st.sidebar.image("images/A2EI_horizontal_white_RGB.png",
                 use_column_width=True)
st.sidebar.text("")
st.sidebar.text("")
st.sidebar.text("")

# Sidebar elements
aam_id = str(st.sidebar.text_input('AAM ID', 945))  # Set System Name

# change to "office" if you are in the A2EI headquarter for faster queries
db_select = "aws"


def init_connection():
    return psycopg2.connect(**st.secrets[db_select])


conn = init_connection()


# set today's date
today = datetime.today()

time_start = st.sidebar.date_input('Start', value=(datetime(2022, 3, 1)))
time_end = st.sidebar.date_input('End', today)

# Database queries
rng = [time_start, time_end]
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
                        ''', conn)
cust = pd.read_sql(f''' SELECT
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
                           skgs_customers
                        WHERE
                           aam_id = {aam_id}
                        ''', conn)

# meta data about system
st.sidebar.text("")
st.sidebar.text("")

st.sidebar.markdown(
    f'<p style="color:#FFFFFF;font-size: 25px;text-align:center;">Meta Data AAM <strong>{aam_id}</strong> <br> </p>', unsafe_allow_html=True)
st.sidebar.markdown(
    f'<p style="color:#FFFFFF;font-size: 20px;">{cust.country[0]} <br> Version {cust.mcu_version[0]} <br> Battery {cust.bat_size[0]} Ah <br> Inverter {cust.inv_size[0]} W <br > Installed on {cust.installation_date[0].strftime("%Y-%m-%d")} <br> Installed by {cust.installation_comp[0]} </p>', unsafe_allow_html=True)

# Data prep
df = df.sort_values(by=['time'])
df['time'] = pd.to_datetime(df['time'])
df.set_index(df['time'], inplace=True)

# Create other usefull columns in df
df_grid = pd.DataFrame(columns=['input_voltage', 'peak_voltage', 'output_voltage',
                                'input_voltage_0tonan', 'peak_voltage_0tonan', 'output_voltage_5tonan', 'grid_avl'])
df_grid['input_voltage'] = df['input_voltage']
df_grid['peak_voltage'] = df['peak_voltage']
df_grid['output_voltage'] = df['output_voltage']
df_grid['input_voltage_0tonan'].mask(
    df_grid['input_voltage'] > 0, df_grid['input_voltage'], inplace=True)  # takes out the 0V data points
df_grid['peak_voltage_0tonan'].mask(
    df_grid['peak_voltage'] > 0, df_grid['peak_voltage'], inplace=True)  # takes out the 0V data points
df_grid['output_voltage_5tonan'].mask(
    df_grid['output_voltage'] > 5, df_grid['output_voltage'], inplace=True)  # takes out the 5V data points

df_grid['grid_avl'].mask(df['input_voltage'] > 0, 1, inplace=True)
df_grid['grid_avl'].mask(df['input_voltage'] == 0, 0, inplace=True)
df_grid['grid_avl'] = df_grid['grid_avl'].fillna(0)  # make all nan to 0 or BL

# df_grid

# resample the 5min data to 1 hour data
hour_data = pd.DataFrame(
    columns=['grid_avl_h', 'grid_avl_h_usb', 'load_w_h', 'pv_w_h'])
hour_data['grid_avl_h'] = df_grid['grid_avl'].resample('H').mean()

# hour_data

# Grouped hourly data to display one typical day
typ_day = pd.DataFrame(
    columns=['avg_grid_avl', 'avg_grid_avl_usb', 'avg_load_w', 'avg_pv_w', 'avg_bat_v'])
typ_day['avg_grid_avl'] = hour_data['grid_avl_h'].groupby(
    hour_data.index.hour).mean()

# typ_day

# group also by day of year to get all the points for every hour to plot box plot
typ_day_all = pd.DataFrame(
    columns=['avg_grid_avl', 'avg_grid_avl_usb', 'avg_load_w', 'avg_pv_w', 'avg_bat_v'])
typ_day_all['avg_grid_avl'] = df_grid['grid_avl'].groupby(
    [df_grid.index.dayofyear.rename('day of year'), df_grid.index.hour.rename('hour')]).mean()

# typ_day_all

# create usefull values from df
avg_input_voltage = round((df_grid['input_voltage_0tonan'].mean()), 1)
min_input_voltage = round((df_grid['input_voltage_0tonan'].min()), 1)
max_input_voltage = round((df_grid['input_voltage_0tonan'].max()), 1)

avg_peak_voltage = round((df_grid['peak_voltage_0tonan'].mean()), 1)
min_peak_voltage = round((df_grid['peak_voltage_0tonan'].min()), 1)
max_peak_voltage = round((df_grid['peak_voltage_0tonan'].max()), 1)


with st.expander('Info'):

    st.warning("under construction")

with st.expander('Data Overview all systems'):

    st.warning("under construction")


with st.expander('Data Overview for AAM '+aam_id):

    # Initial Plot

    final = make_subplots(specs=[[{"secondary_y": True}]])
    final.add_trace(go.Scatter(
        x=df.index, y=df['input_voltage'], name='input_voltage',  line_color='rgba(82, 82, 82, .8)'))
    final.add_trace(go.Scatter(
        x=df.index, y=df['peak_voltage'], name='peak_volatge',  line_color='rgb(245, 237, 111)'))
    final.add_trace(go.Scatter(
        x=df.index, y=df['output_voltage'], name='output_voltage', line_color='rgb(251, 117, 157)'))
    # final.add_trace(go.Scatter(x = dfnew.index, y = dfnew['charging_output_voltage'], name =  'Battery Voltage mppt(V)', line_color = 'rgb(29, 100, 150)', line = dict(width = 3)), secondary_y = True)
    final.update_layout(plot_bgcolor='white',
                        showlegend=True,
                        font=dict(size=12),
                        width=500,
                        height=300,
                        title={
                            'text':  "AAM ID: " + aam_id,
                            'y': 0.9,
                            'x': 0.5,
                            'xanchor': 'center',
                            'yanchor': 'top'})
    final.update_xaxes(  # dtick = 14,
        tickformat='%d/%m',
        ticks='outside',
        gridcolor='lightgrey',
        linecolor='lightgrey')

    final.update_xaxes(title="Hour of the Day",
                       row=2, col=1)

    final.update_yaxes(title_text='Voltage (V)',
                       showgrid=True,
                       secondary_y=False,
                       showline=True,
                       linewidth=1,
                       linecolor='lightgrey',
                       showticklabels=True,
                       gridcolor='lightgrey',
                       ticks='outside',
                       range=[0, 300])

    st.plotly_chart(final, use_container_width=True)

    st.warning("under construction")
# -------------------------------------------


with st.expander('Grid Analysis'):

    st.markdown("<h3 style='text-align: center'>Input and Output Voltage (AC)</h3>",
                unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        fig = go.Figure()

        fig.add_trace(go.Scatter(x=df_grid.index,
                                 y=df_grid['input_voltage_0tonan'], name="Grid Input Voltage Inverter",
                                 line_shape='linear', line_color='lightslategrey', line_width=1.5))

        fig.add_trace(go.Scatter(x=df_grid.index,
                                 y=df_grid['peak_voltage_0tonan'], name="Grid Input Voltage MCU",
                                 line_shape='linear', line_width=1.5,
                                 line=dict(color='GoldenRod')))
        fig.add_trace(go.Scatter(x=df_grid.index,
                                 y=df_grid['output_voltage_5tonan'], name="AAM Output Voltage",
                                 line_shape='linear', line_color='rgb(223,116,149)', line_width=1.5))

        annotation_min = "Min: "+str(min_input_voltage) + " V"
        annotation_max = "Max: "+str(max_input_voltage) + " V"

        fig.update_layout(  # title='Grid Data',
            plot_bgcolor='white',
            xaxis=dict(
                showline=True,
                showgrid=True,
                showticklabels=True,
                linewidth=1.5,
                ticks='outside',
                title="Time",
                gridcolor='lightgrey',
                linecolor='lightgrey',
                mirror=True,
                tickformat='%d/%m %H:%M',  # %H:%M',
                tickfont=dict(family="Fugue", size=12, color='Black')
                # range=[0,110],
            ),
            yaxis=dict(
                title=" Grid Voltage in V",
                showgrid=True,
                zeroline=True,
                showline=True,
                linewidth=1.5,
                ticks='outside',
                linecolor='lightgrey',
                mirror=True,
                showticklabels=True,
                gridcolor='lightgrey',
                tickfont=dict(family="Fugue", size=12, color='Black'),
                range=[100, 250],
            ),
            font=dict(family="Fugue", size=12, color='black'),
            autosize=False,
            width=300, height=300,
            margin=dict(l=15, r=15, b=15, t=15,  pad=2),
            showlegend=False,
            legend=dict(title="",
                        orientation="h",
                        yanchor="top",
                        y=.95,
                        xanchor="center",
                        traceorder='normal',
                        x=0.5,
                        ),
        )

        st.plotly_chart(fig, use_container_width=True)
        # fig.write_image("grid_V_time_plot.pdf")

    #################
    with col2:
        fig = go.Figure()

        fig.add_trace(go.Box(y=df_grid['input_voltage_0tonan'], name="input_voltage",
                             marker_color='lightslategrey'))
        fig.add_trace(go.Box(y=df_grid['peak_voltage_0tonan'], name="peak_voltage",
                             marker_color='GoldenRod'))
        fig.add_trace(go.Box(y=df_grid['output_voltage'], name="output_voltage",
                             marker_color='rgb(223,116,149)'))

        fig.update_layout(  # title='Grid Data',
            plot_bgcolor='white',
            xaxis=dict(
                showline=True,
                showgrid=True,
                showticklabels=False,
                linewidth=1.5,
                ticks='outside',
                title="",
                gridcolor='lightgrey',
                linecolor='lightgrey',
                mirror=True,
                tickformat='%d/%m %H:%M',  # %H:%M',
                tickfont=dict(family="Fugue", size=12, color='Black')
                # range=[0,110],
            ),
            yaxis=dict(
                title=" Grid Voltage in V",
                showgrid=True,
                zeroline=True,
                showline=True,
                linewidth=1.5,
                ticks='outside',
                linecolor='lightgrey',
                mirror=True,
                showticklabels=True,
                gridcolor='lightgrey',
                tickfont=dict(family="Fugue", size=12, color='Black'),
                range=[100, 250],
            ),
            font=dict(family="Fugue", size=12, color='black'),
            autosize=False,
            width=300, height=300,
            margin=dict(l=15, r=15, b=15, t=15,  pad=2),
            showlegend=True,
            legend=dict(title="",
                        orientation="v",
                        yanchor="bottom",
                        y=0.05,
                        xanchor="right",
                        traceorder='normal',
                        x=0.95,
                        ),
        )
        st.plotly_chart(fig, use_container_width=True)
        # fig.write_image("grid_V_box_plot.pdf")
    #########################################

    col1, col2 = st.columns([1, 1])
    with col1:
        st.info('avg_input_voltage: '+str(avg_input_voltage))
        st.info('min_input_voltage: '+str(min_input_voltage))
        st.info('max_input_voltage: '+str(max_input_voltage))

    with col2:
        st.info('avg_peak_voltage: '+str(avg_peak_voltage))
        st.info('min_peak_voltage: '+str(min_peak_voltage))
        st.info('max_peak_voltage: '+str(max_peak_voltage))

    ##########################################
    ################################

    st.markdown("<h3 style='text-align: center'>Hourly Grid Availability Profile</h3>",
                unsafe_allow_html=True)

    ###########################################
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=typ_day.index,
                             y=typ_day['avg_grid_avl'], name="grid availability mean",
                             line_shape='linear', line_color='lightslategrey', line_width=4,))

    fig.add_trace(go.Box(y=typ_day_all['avg_grid_avl'], x=typ_day_all.index.get_level_values(1)+1, marker_color='darkgrey',
                         jitter=0.3,
                         # pointpos=-1.8,
                         # boxpoints='all',
                         ))

    fig.update_layout(  # title='Hourly grid availability profile USB',
                        plot_bgcolor='white',
                        xaxis=dict(
                            showline=True,
                            showgrid=True,
                            showticklabels=True,
                            linewidth=1.5,
                            ticks='outside',
                            title="hour",
                            gridcolor='lightgrey',
                            linecolor='lightgrey',
                            mirror=True,
                            # tickformat='%d/%m %H:%M', #%H:%M',
                            tickfont=dict(family="Fugue",
                                          size=12, color='Black'),
                            range=[0.5, 24.5],
                            dtick=1,
                        ),
        yaxis=dict(
                            title=" Probability of grid availability in %",
                            # showgrid=True,
                            zeroline=True,
                            showline=True,
                            linewidth=1.5,
                            linecolor='lightgrey',
                            mirror=True,
                            showticklabels=True,
                            gridcolor='lightgrey',
                            tickfont=dict(family="Fugue",
                                          size=12, color='Black'),
                            # range=[140,250],
                            dtick=0.1,
                            ticks='outside',
                            tickformat='0.0%',
                        ),
        font=dict(family="Fugue", size=12, color='black'),
        autosize=False,
        width=600, height=300,
        margin=dict(l=15, r=15, b=15, t=15,  pad=2),
        showlegend=False,
        legend=dict(title="",
                            orientation="h",
                            yanchor="bottom",
                            y=1.05,
                            xanchor="center",
                            traceorder='normal',
                            x=0.5,
                    ),
    )

    st.plotly_chart(fig, use_container_width=True)
    # fig.write_image("hour_profile.pdf")

################################
