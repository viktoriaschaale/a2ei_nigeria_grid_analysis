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
                        ''' , conn)

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

#### DATA PREP

#Original table
df = df.sort_values(by = ['time'])
df['time'] = pd.to_datetime(df['time'])
df.set_index(df['time'],inplace=True)

grid_sensor = st.sidebar.selectbox(
     "Grid measured by:",
     ('Inverter', 'MCU'))

### TABLES

#df_grid
df_grid=pd.DataFrame(columns=['input_voltage','output_voltage','input_voltage_0tonan','output_voltage_5tonan','grid_avl','grid_on_time','grid_off_time','aam_on_time','aam_off_time'])
if grid_sensor == 'Inverter':
    df_grid['input_voltage']=df['input_voltage']
else:
    df_grid['input_voltage']=df['peak_voltage']
df_grid['output_voltage']=df['output_voltage']
df_grid['input_voltage_0tonan'].mask(df_grid['input_voltage']>0,df_grid['input_voltage'],inplace=True) #takes out the 0V data points
df_grid['output_voltage_5tonan'].mask(df_grid['output_voltage']>5,df_grid['output_voltage'],inplace=True) #takes out the 5V data points

df_grid['grid_avl'].mask(df['input_voltage']>0,1,inplace=True)
df_grid['grid_avl'].mask(df['input_voltage']==0,0,inplace=True)
df_grid['grid_avl']=df_grid['grid_avl'].fillna(0)#make all nan to 0 or BL

#writes 5 min in the dataset when grid voltage was higher or lower than 180V 
df_grid['grid_on_time'].mask(df_grid['grid_avl']>0,5, inplace=True)#inplace overwrite the original data frame
df_grid['grid_on_time'].replace(np.nan,0 ,inplace=True) #make all nan to 0 or BL 
df_grid['grid_off_time'].mask(df_grid['grid_avl']==0,5, inplace=True)

df_grid['aam_on_time'].mask(df['input_voltage']>=0,5, inplace=True)
df_grid['aam_off_time'].mask(np.isnan(df['input_voltage']),5,inplace=True)

df_grid['counter_evt'] = df_grid['grid_avl'].diff().ne(0).cumsum()
df_grid['counter_bl']  = df_grid['grid_avl'].diff() 
df_grid['counter_bl']  = df_grid['counter_bl'].replace([1],0) #makes the 1 to 0 transtion back to 0 just to count BL

#hour_data
#resample the 5min data to 1 hour data
hour_data= pd.DataFrame(columns=['grid_avl_h','grid_avl_h_usb','load_w_h','pv_w_h'])
hour_data['grid_avl_h']=df_grid['grid_avl'].resample('H').mean()

#daily_data
daily_data= pd.DataFrame(columns=['E_Wh_daily','grid_on_time_daily','grid_off_time_daily','consumption','bl_daily'])
daily_data['grid_on_time_daily']=df_grid['grid_on_time'].resample('D').sum()/60
daily_data['grid_off_time_daily']=df_grid['grid_off_time'].resample('D').sum()/60
daily_data['aam_on_time_daily']=df_grid['aam_on_time'].resample('D').sum()/60
daily_data['aam_off_time_daily']=df_grid['grid_off_time'].resample('D').sum()/60

daily_data['bl_daily']=abs(df_grid['counter_bl'].resample('D').sum())

#monthly_data
monthly_data=pd.DataFrame(columns=[])
monthly_data['bl_monthly']=abs(df_grid['counter_bl'].resample('M').sum())

#typ_day
#Grouped hourly data to display one typical day
typ_day=pd.DataFrame(columns=['avg_grid_avl','avg_grid_avl_usb','avg_load_w','avg_pv_w','avg_bat_v'])
typ_day['avg_grid_avl']=hour_data['grid_avl_h'].groupby(hour_data.index.hour).mean()

#typ_day_all
#group also by day of year to get all the points for every hour to plot box plot
typ_day_all=pd.DataFrame(columns=['avg_grid_avl','avg_grid_avl_usb','avg_load_w','avg_pv_w','avg_bat_v'])
typ_day_all['avg_grid_avl']=df_grid['grid_avl'].groupby([df_grid.index.dayofyear.rename('day of year'),df_grid.index.hour.rename('hour')]).mean()

#Data frame counting grid events ON/OFF
df_grid_evt=pd.DataFrame(columns=[])
df_grid_evt = df_grid.groupby('counter_evt')['grid_avl'].min().to_frame(name='grid_avl').join(df_grid.groupby('counter_evt')['grid_avl'].count().rename('length'))
df_grid_evt['length_h']=df_grid_evt['length']*5/60 #lenght blackuts in hours #.mask(df_grid_evt['grid_avl']!=0)
df_grid_evt.drop(df_grid_evt.tail(2).index,inplace = True) #drop first and last row, normally this events are not complete
df_grid_evt.drop(df_grid_evt.head(2).index,inplace = True)

#get just on grid off events
df_grid_evt_off=pd.DataFrame(columns=[])
df_grid_evt_off=df_grid_evt[df_grid_evt['grid_avl']==0 ].sort_values(by = 'length_h')#, ascending = False)
df_grid_evt_off.reset_index(drop=True, inplace=True)
df_grid_evt_off.index = df_grid_evt_off.index + 1


### VALUES

# create usefull values from df
avg_input_voltage = round((df_grid['input_voltage_0tonan'].mean()), 1)
min_input_voltage = round((df_grid['input_voltage_0tonan'].min()), 1)
max_input_voltage = round((df_grid['input_voltage_0tonan'].max()), 1)

grid_on_time_all=round((sum(daily_data['grid_on_time_daily'])),1)
grid_off_time_all=round((sum(daily_data['grid_off_time_daily'])),1)

aam_on_time_all=round((sum(daily_data['aam_on_time_daily'])),1)
aam_off_time_all=round((sum(daily_data['aam_off_time_daily'])),1)

avg_bl_duration = round((df_grid_evt_off['length_h'].mean()),1)
max_bl_duration = round((df_grid_evt_off['length_h'].max()),1) 
min_bl_duration = round((df_grid_evt_off['length_h'].min()),1)

avg_bl_nu_daily = round((daily_data['bl_daily'].mean()),1)
min_bl_nu_daily = round((daily_data['bl_daily'].min()),1)
max_bl_nu_daily = round((daily_data['bl_daily'].max()),1)

avg_bl_nu_monthly = round((monthly_data['bl_monthly'].mean()),1)
min_bl_nu_monthly = round((monthly_data['bl_monthly'].min()),1)
max_bl_nu_monthly = round((monthly_data['bl_monthly'].max()),1)

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

#### Grid Analysis

with st.expander('Grid Analysis'):

    st.markdown("<h3 style='text-align: center'>Input and Output Voltage (AC)</h3>",
                unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        fig = go.Figure()

        fig.add_trace(go.Scatter(x=df_grid.index, 
                                    y=df_grid['input_voltage_0tonan'], name="Grid Input Voltage",
                                    line_shape='linear',line_color='lightslategrey',line_width=1.5))            

 
        fig.add_trace(go.Scatter(x=df_grid.index, 
                                    y=df_grid['output_voltage_5tonan'], name="AAM Output Voltage",
                                    line_shape='linear',line_color='rgb(223,116,149)',line_width=1.5))

        annotation_min= "Min: "+str(min_input_voltage) +" V"
        annotation_max= "Max: "+str(max_input_voltage) +" V"
        
        fig.update_layout(#title='Grid Data',
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
                                tickformat='%d/%m %H:%M', #%H:%M',
                                tickfont=dict(family="Fugue",size=12, color='Black')
                                #range=[0,110],
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
                                tickfont=dict(family="Fugue",size=12, color='Black'),
                                range=[100,250],
                                ),
                            font=dict( family="Fugue", size=12, color='black'),
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
        #fig.write_image("grid_V_time_plot.pdf")

    #################
    with col2:
        fig = go.Figure()
        
        fig.add_trace(go.Box(y=df_grid['input_voltage_0tonan'],name="input_voltage",
                            marker_color = 'lightslategrey'))

        fig.add_trace(go.Box(y=df_grid['output_voltage'],name="output_voltage",
                            marker_color = 'rgb(223,116,149)'))
            
        fig.update_layout(#title='Grid Data',
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
                                tickformat='%d/%m %H:%M', #%H:%M',
                                tickfont=dict(family="Fugue",size=12, color='Black')
                                #range=[0,110],
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
                                tickfont=dict(family="Fugue",size=12, color='Black'),
                                range=[100,250],
                                ),
                            font=dict( family="Fugue", size=12, color='black'),
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

    st.info('avg_input_voltage: '+str( avg_input_voltage))
    st.info('min_input_voltage: '+str( min_input_voltage))
    st.info('max_input_voltage: '+str( max_input_voltage))
    
        
    ##########################################

    st.markdown("<h3 style='text-align: center'>Grid and AAM Availability</h3>", unsafe_allow_html=True)
        
    col1, col2= st.columns([1,1])
    with col1:
        labels = ['Grid On','Grid Off']
        values = [grid_on_time_all, grid_off_time_all]
        colors = ['GoldenRod','lightslategrey']
        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.8 )])
        fig.update_traces(hoverinfo='label+percent', textinfo='label+percent',textfont_size=12,
                        marker=dict(colors=colors, line=dict(color='#000000', width=2)))
        fig.update_layout(annotations=[dict(text="Grid Availability", x=0.5, y=0.5, font_size=12, showarrow=False)])
        fig.update_layout(font=dict( family="Fugue", size=12, color='black'),
                            autosize=False,
                        width=300, height=300,
                        margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                            showlegend=False)
        st.plotly_chart(fig,use_container_width=True)

        #fig.write_image("grid_availability.pdf")


    with col2:
        labels = ['AAM Available','AAM Not Available']
        values = [aam_on_time_all, aam_off_time_all]
        colors = ['rgb(223,116,149)','DarkSlateGrey']
        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.8 )])
        fig.update_traces(hoverinfo='label+percent', textinfo='label+percent', textfont_size=12,
                        marker=dict(colors=colors, line=dict(color='#000000', width=2)))
        fig.update_layout(annotations=[dict(text="AAM Availability <br> All Day", x=0.5, y=0.5, font_size=12, showarrow=False)])
        fig.update_layout(font=dict( family="Fugue", size=12, color='black'),
                            autosize=False,
                        width=300, height=300,
                        margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                            #margin=dict(l=75, r=75, b=80, t=80,  pad=2),
                            showlegend=False,
                            )
        st.plotly_chart(fig,use_container_width=True)
        #fig.write_image("AAM_availability.pdf")

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
        
    st.markdown("<h3 style='text-align: center'>Power Outage Duration</h3>", unsafe_allow_html=True)

    col1, col2,col3= st.columns([1,1,1])
    col1.subheader('Duration sorted by length')
    col2.subheader('Histogram ')
    col3.subheader('Distribution')
    
    with col1:
    
    
        fig = go.Figure([go.Bar(y=df_grid_evt_off['length_h'], x=df_grid_evt_off.index, 
                                name='Blackouts per day',
                                marker_color='lightslategrey')],)
        annotation_avg= "Avg: "+str(avg_bl_duration) +" hours"
        annotation_max= "Max: "+str(max_bl_duration) +" hours"
        annotation_min= "Min: "+str(min_bl_duration) +" hours"

        fig.add_hline(y=avg_bl_duration, 
                            annotation_text= annotation_avg,
                            line_color='dimgrey',
                            annotation_position="bottom left",
                            line_width=1,
                                line_dash='dash')
        fig.add_hline(y=max_bl_duration,
                            annotation_text= annotation_max,
                            line_color='dimgrey',
                            annotation_position="bottom left",
                            line_width=1,
                                line_dash='dash')
        fig.add_hline(y=min_bl_duration, 
                            annotation_text= annotation_min,
                            line_color='dimgrey',
                            annotation_position="bottom left",
                            line_width=1,
                                line_dash='dash')
        
        fig.update_layout(#title='Grid Data',
                            plot_bgcolor='white',
                            xaxis=dict(
                                showline=True,
                                showgrid=True,
                                showticklabels=True,
                                linewidth=1.5,
                                ticks='outside',
                                title="Blackout events",
                                gridcolor='lightgrey',
                                linecolor='lightgrey',
                                mirror=True,
                                #tickformat='%d/%m %H:%M', #%H:%M',
                                tickfont=dict(family="Fugue",size=12, color='Black')
                                #range=[0,110],
                                ),
                            yaxis=dict(
                                title= 'Lenght of Blackout in h',
                                showgrid=True,
                                zeroline=True,
                                showline=True,
                                linewidth=1.5,
                                ticks='outside',
                                linecolor='lightgrey',
                                mirror=True,
                                showticklabels=True,
                                gridcolor='lightgrey',
                                tickfont=dict(family="Fugue",size=12, color='Black'),
                                #range=[140,250],
                                ),
                            font=dict( family="Fugue", size=12, color='black'),
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
        #fig.write_image("bl_duration_plot.pdf")
        
    
        
        
        ####################################   HISTOGRAM   ##############################################
    with col3:
        
        fig = go.Figure()

        fig.add_trace(go.Histogram(x=df_grid_evt_off['length_h'],histnorm='percent',marker_color='rgb(223,116,149)',cumulative_enabled=False,name='Histogram'))
        fig.add_trace(go.Histogram(x=df_grid_evt_off['length_h'],histnorm='percent',marker_color='lightslategrey',cumulative_enabled=True,name='Cumulative Histogram'))
                                #name='Blackouts per day',
                                #marker_color='DarkSeaGreen')],)
        #fig.add_vline(x=avg_bl_bat_h, 
            #                   annotation_text= annotation_load,
            #                   line_color='dimgrey',
            #                 annotation_position="bottom left",
            #                 line_width=1,
            #               line_dash='dash',)
        fig.update_traces(xbins=dict( # bins used for histogram
                            #start=0.0,
                            #end=10.0,
                            size=1),
                            autobinx = False)

        fig.update_layout(  #title_text='Histogram', # title of plot
                            xaxis_title_text='Lenght of Blackout in h', # xaxis label
                            yaxis_title_text='Percentage of Blackouts in %', # yaxis label
                            bargap=0.1, # gap between bars of adjacent location coordinates
                            #bargroupgap=0.1 # gap between bars of the same location coordinates
                            autosize=False,
                            width=300, height=300,
                            margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                            legend=dict(title="",
                                        orientation="h",
                                        yanchor="top",
                                        y=1,
                                        xanchor="left",
                                        traceorder='normal',
                                        x=0,
                                        font=dict(
                                    family="Fugue",
                                    size=12,
                                    color='black'
                                    ),
                                        ),
                            plot_bgcolor='white',
                            font=dict(
                                    family="Fugue",
                                    size=12,
                                    color='black'
                                    ),
                            xaxis=dict(
                                range=[0,10],
                                showline=True,
                                showgrid=False,
                                showticklabels=True,
                                linewidth=1.5,
                                ticks='outside',
                                #title="Day/Month",
                                gridcolor='lightgrey',
                                linecolor='lightgrey',
                                mirror=True,
                                #tickformat='%',
                                tick0 = 1,
                                dtick = 1,
                                ),
                            yaxis=dict(
                                range=[0,110],
                                #title=" Number of Power Outages per day",
                                showgrid=True,
                                zeroline=True,
                                showline=True,
                                linewidth=1.5,
                                ticks='outside',
                                linecolor='lightgrey',
                                mirror=True,
                                showticklabels=True,
                                gridcolor='lightgrey',
                                #tickformat='%',
                                )
                                    #color='rgb(82, 82, 82)',),)
                        )
        st.plotly_chart(fig,use_container_width=True)
    
        #fig.write_image("Histogramm_945.pdf")
        
    with col2:      
        fig = go.Figure()
        


        fig.add_trace(go.Box(y=df_grid_evt_off['length_h'],name="length_h",
                            marker_color = 'lightslategrey'))
    
        fig.update_layout(#title='Grid Data',
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
                                tickformat='%d/%m %H:%M', #%H:%M',
                                tickfont=dict(family="Fugue",size=12, color='Black')
                                #range=[0,110],
                                ),
                            yaxis=dict(
                                title=" Length of blackout in h",
                                showgrid=True,
                                zeroline=True,
                                showline=True,
                                linewidth=1.5,
                                ticks='outside',
                                linecolor='lightgrey',
                                mirror=True,
                                showticklabels=True,
                                gridcolor='lightgrey',
                                tickfont=dict(family="Fugue",size=12, color='Black'),
                                #range=[0,300],
                                ),
                            font=dict( family="Fugue", size=12, color='black'),
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
        #fig.write_image("grid_V_box_plot.pdf")
        
        ##################################################################################

    ##################################################################################
    st.markdown("<h3 style='text-align: center'>Power Outage Frequency</h3>", unsafe_allow_html=True)


    col1, col2, col3= st.columns([1,1,1])
    col1.subheader('Daily')
    col2.subheader('Monthly')
    col3.subheader('Distribution')
    with col1:

        fig = go.Figure([go.Bar(y=daily_data['bl_daily'], x=daily_data.index, 
                                name='Blackouts per day',
                                marker_color='lightslategrey')],)

        annotation_avg= "Avg: "+str(avg_bl_nu_daily) +" "
        fig.add_hline(y=avg_bl_nu_daily, 
                            annotation_text= annotation_avg,
                            line_color='dimgrey',
                            annotation_position="bottom left",
                            line_width=1,
                                line_dash='dash')
        annotation_min= "Min: "+str(min_bl_nu_daily) +" "
        fig.add_hline(y=min_bl_nu_daily, 
                            annotation_text= annotation_min,
                            line_color='dimgrey',
                            annotation_position="bottom left",
                            line_width=1,
                                line_dash='dash')
        annotation_max= "Max: "+str(max_bl_nu_daily) +" "
        fig.add_hline(y=max_bl_nu_daily, 
                            annotation_text= annotation_max,
                            line_color='dimgrey',
                            annotation_position="bottom left",
                            line_width=1,
                                line_dash='dash')
        fig.update_layout(  
                            plot_bgcolor='white',
                            xaxis=dict(
                                showline=True,
                                showgrid=True,
                                showticklabels=True,
                                linewidth=1.5,
                                ticks='outside',
                                title="Day/Month",
                                gridcolor='lightgrey',
                                linecolor='lightgrey',
                                mirror=True,
                                tickformat='%d/%m', #%H:%M',
                                tickfont=dict(family="Fugue",size=12, color='Black')
                                #range=[0,110],
                                ),
                            yaxis=dict(
                                title=" Number of Power Outages per day",
                                showgrid=True,
                                zeroline=True,
                                showline=True,
                                linewidth=1.5,
                                ticks='outside',
                                linecolor='lightgrey',
                                mirror=True,
                                showticklabels=True,
                                gridcolor='lightgrey',
                                tickfont=dict(family="Fugue",size=12, color='Black'),
                                #range=[140,250],
                                ),
                            font=dict( family="Fugue", size=12, color='black'),
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
        #fig.write_image("bl_freq_d.pdf")
        
        
    ###############################
    with col2:

        fig = go.Figure([go.Bar(y=monthly_data['bl_monthly'], x=monthly_data.index, 
                                name='Power Outages per month',
                                xperiod="M1",
                                xperiodalignment="middle",
                                marker_color='lightslategrey')],)

        #annotation_avg= "Max: "+str(max_bl_nu_m) +" "
        #fig.add_hline(y=max_bl_nu_m, 
        #                    annotation_text= annotation_avg,
        #                    line_color='dimgrey',
        #                    annotation_position="bottom left",
        #                    line_width=1,
        #                     line_dash='dash')
        #annotation_min= "Min: "+str(min_bl_nu_m) +" "
        #fig.add_hline(y=min_bl_nu, 
        #                    annotation_text= annotation_min,
        #                    line_color='dimgrey',
        #                    annotation_position="bottom left",
        #                    line_width=1,
        #                     line_dash='dash')
        annotation_max= "AVG: "+str(avg_bl_nu_monthly) +" "
        fig.add_hline(y=avg_bl_nu_monthly, 
                            annotation_text= annotation_max,
                            line_color='dimgrey',
                            annotation_position="bottom left",
                            line_width=1,
                                line_dash='dash')
        fig.update_layout(  
                            plot_bgcolor='white',
                            xaxis=dict(
                                showline=True,
                                showgrid=True,
                                showticklabels=True,
                                linewidth=1.5,
                                ticks='outside',
                                title="Month",
                                gridcolor='lightgrey',
                                linecolor='lightgrey',
                                mirror=True,
                                dtick="M1",
                                ticklabelmode="period",
                                tickformat="%b",
                                #tickformat='%m', #%H:%M',
                                tickfont=dict(family="Fugue",size=12, color='Black')
                                #range=[0,110],
                                ),
                            yaxis=dict(
                                title=" Number of Power Outages per month",
                                showgrid=True,
                                zeroline=True,
                                showline=True,
                                linewidth=1.5,
                                ticks='outside',
                                linecolor='lightgrey',
                                mirror=True,
                                showticklabels=True,
                                gridcolor='lightgrey',
                                tickfont=dict(family="Fugue",size=12, color='Black'),
                                #range=[140,250],
                                ),
                            font=dict( family="Fugue", size=12, color='black'),
                            autosize=False,
                            width=300, height=300,
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
        #fig.write_image("bl_freq_m.pdf")
        
        
        
    with col3:      
        fig = go.Figure()
        


        fig.add_trace(go.Box(y=daily_data['bl_daily'],name="bl_daily",
                            marker_color = 'lightslategrey'))
    
        fig.update_layout(#title='Grid Data',
                            plot_bgcolor='white',
                            xaxis=dict(
                                showline=True,
                                showgrid=True,
                                showticklabels=False,
                                linewidth=1.5,
                                ticks='outside',
                                title="Series",
                                gridcolor='lightgrey',
                                linecolor='lightgrey',
                                mirror=True,
                                tickformat='%d/%m %H:%M', #%H:%M',
                                tickfont=dict(family="Fugue",size=12, color='Black')
                                #range=[0,110],
                                ),
                            yaxis=dict(
                                title="Lenght of Blackout in h",
                                showgrid=True,
                                zeroline=True,
                                showline=True,
                                linewidth=1.5,
                                ticks='outside',
                                linecolor='lightgrey',
                                mirror=True,
                                showticklabels=True,
                                gridcolor='lightgrey',
                                tickfont=dict(family="Fugue",size=12, color='Black'),
                                #range=[0,300],
                                ),
                            font=dict( family="Fugue", size=12, color='black'),
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
        #fig.write_image("grid_V_box_plot.pdf")
