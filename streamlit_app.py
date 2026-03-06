import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="PXE Cooker Analysis",
    page_icon=":bar_chart:",
    layout="wide"
)

load_file = st.sidebar.file_uploader("Select Data File to Analyse", type=["csv"])
st.header(f"{load_file.name[0:9] if load_file else 'PXE Cooker Analysis'}")
st.divider  ()

if load_file is not None:
   
   
    df = pd.read_csv(load_file, header=None)
    # Combine date (col 0) and time (col 1) into a single datetime column
    df['datetime'] = pd.to_datetime(df[0].astype(str) + ' ' + df[1].astype(str), errors='coerce', dayfirst=True)


    # Keep only rows with a valid datetime (power ON)
    df_on = df.dropna(subset=['datetime']).copy()
    df_on['Date'] = df_on['datetime'].dt.date

    st.sidebar.header("Data Filters")
    # --- Date filter calendar widget in sidebar ---
    min_date = df_on['Date'].min()
    max_date = df_on['Date'].max()
    date_range = st.sidebar.date_input(
        'Date range',
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    st.sidebar.header("Options:")

    options = st.sidebar.multiselect('View/Hide Sctions',options=['Run Time', 'Oil Temperature', 'Pressure', 'Errors', 'Pump Runs'], default=['Run Time', 'Oil Temperature', 'Pressure', 'Errors', 'Pump Runs'])  
   

    run_time = 'Run Time' in options
    oil_temp = 'Oil Temperature' in options
    pressure = 'Pressure' in options
    errors = 'Errors' in options
    pump_runs = 'Pump Runs' in options

   
    # Ensure date_range is always a tuple (start, end)
    if isinstance(date_range, tuple):
        start_date, end_date = date_range
    else:
        start_date = end_date = date_range
    # Filter df_on by selected date range
    df_on = df_on[(df_on['Date'] >= start_date) & (df_on['Date'] <= end_date)]

    # Also filter first_last for run time table
    first_last = df_on.groupby('Date')['datetime'].agg(['first', 'last'])
    first_last['interval'] = first_last['last'] - first_last['first']

    # First and last timestamp per day
    first_last = df_on.groupby('Date')['datetime'].agg(['first', 'last'])
    first_last['interval'] = first_last['last'] - first_last['first']
    

    #### ---- Main Page Layout ---- ####
   
    if run_time:
        col1, col2 = st.columns([1,3])
        with col1:
            # Rename columns for display
            display_first_last = first_last.rename(columns={
                'first': 'Turn On',
                'last': 'Turn Off',
                'interval': 'Run Time'
            })
            styled_first_last = display_first_last.style.format({
                'Turn On': lambda x: x.strftime('%H:%M'),
                'Turn Off': lambda x: x.strftime('%H:%M'),
                'Run Time': lambda x: f"{x.total_seconds() / 3600:.2f} hours"
            })
            st.header("On/Off Times")
            st.dataframe(styled_first_last)

        # Autodetect the most common time difference (in seconds)
        intervals = df_on['datetime'].sort_values().diff().dropna().dt.total_seconds()
        if not intervals.empty:
            interval_seconds = intervals.mode()[0]
        else:
            interval_seconds = 60  # fallback to 1 minute if only one timestamp

        # Count ON intervals per day
        on_counts = df_on.groupby('Date').size()

        # Calculate run time in hours per day as the interval (last - first) per day
        run_time_hours = first_last['interval'].dt.total_seconds() / 3600

       
        with col2:

            # Bar chart for hours run per day
            st.header("Cooker run time per day (hours)")
            st.bar_chart(run_time_hours)
    if oil_temp:
        # --- Oil temperature analysis ---
        # Convert column 7 (index 6) to numeric (Fahrenheit)
        df_on['oil_temp_F'] = pd.to_numeric(df_on[6], errors='coerce')
        # Convert to Celsius
        df_on['oil_temp_C'] = (df_on['oil_temp_F'] - 32) * 5.0/9.0

        # Line graph of oil temperature in Celsius
        
        temp_chart_data = df_on[['datetime', 'oil_temp_C']].set_index('datetime')
        #st.line_chart(temp_chart_data)

        # Median temperature per day (Celsius)
        median_temp_per_day = df_on.groupby('Date')['oil_temp_C'].median()
        
        # Overlay median on line chart (optional, for advanced visualization)
        

        st.header("Oil Temperature Analysis")
        import altair as alt
        chart = alt.Chart(df_on).mark_line().encode(
            x='datetime:T',
            y=alt.Y('oil_temp_C', title='Oil Temp (°C)'),
            tooltip=['datetime', 'oil_temp_C']
        ).properties(title='Oil Temperature (°C) Over Time')
        median_points = alt.Chart(df_on).mark_point(color='red').encode(
            x='datetime:T',
            y='oil_temp_C'
        )
        # Median per day as a step line
        median_df = median_temp_per_day.reset_index()
        median_df['datetime'] = pd.to_datetime(median_df['Date'])
        median_line = alt.Chart(median_df).mark_line(color='orange').encode(
            x='datetime:T',
            y=alt.Y('oil_temp_C', title='Median Oil Temp (°C)'),
            tooltip=['Date', 'oil_temp_C']
        )
        st.altair_chart(chart + median_line, use_container_width=True)
    if pressure:
        # --- Oil level analysis ---
        st.header("Oil Level Analysis")
        # Convert column 8 (index 7) to numeric
        df_on['oil_level'] = pd.to_numeric(df_on[7], errors='coerce')
        oil_level_chart = df_on[['datetime', 'oil_level']].set_index('datetime')
        st.line_chart(oil_level_chart, use_container_width=True)

        # --- Pressure analysis ---
        st.header("Pressure Analysis (PSI)")
        # Convert column 20 (index 19) to numeric (PSI)
        df_on['pressure_psi'] = pd.to_numeric(df_on[19], errors='coerce')
        # Use Altair for custom y-axis
        import altair as alt
        pressure_chart = alt.Chart(df_on).mark_line().encode(
            x=alt.X('datetime:T', title='Time'),
            y=alt.Y('pressure_psi', title='Pressure (PSI)', scale=alt.Scale(domain=[0, 16])),
            tooltip=['datetime', 'pressure_psi']
        ).properties(title='Pressure (PSI) Over Time')
        st.altair_chart(pressure_chart, use_container_width=True)
   

    if pump_runs:
        # --- Pump run counter per day ---
        # Column 14 (index 13): 'FP' = start, 'xFP' = stop
        df_on['pump_flag'] = df_on[23].astype(str)
        pump_starts = df_on[df_on['pump_flag'] == ' FltrPump On']
        pump_runs_per_day = pump_starts.groupby('Date').size().rename('Pump Runs')
        st.header('Pump Run Count Per Day')
    #    st.dataframe(pump_runs_per_day)
        st.bar_chart(pump_runs_per_day)


    if errors:

        # --- Most common errors table ---
        # Error column is column 17 (index 16)
        st.write("Most common errors:")
        error_counts = df_on[16].value_counts().reset_index()
        error_counts.columns = ['Error', 'Count']
        st.dataframe(error_counts)

    # --- Cook and Pressure Cycles per Day ---
    # Column 22 (index 21): "* BEG COOK" for cook cycle
    # Column 24 (index 23): " Pr Outp On" for pressure cycle
    df_on['cook_flag'] = df_on[21].astype(str)
    df_on['pressure_flag'] = df_on[23].astype(str)
    cook_cycles = df_on[df_on['cook_flag'].str.contains("\* BEG COOK")]
    pressure_cycles = df_on[df_on['pressure_flag'].str.contains(" Pr Outp On")]
    cook_cycles_per_day = cook_cycles.groupby('Date').size().rename('Cook Cycles')
    pressure_cycles_per_day = pressure_cycles.groupby('Date').size().rename('Pressure Cycles')
    # Combine into one DataFrame for cluster bar chart
    cycles_df = pd.concat([cook_cycles_per_day, pressure_cycles_per_day], axis=1).fillna(0).astype(int)
    st.header('Cook and Pressure Cycles Per Day')
    st.dataframe(cycles_df)
    # Cluster bar chart using Altair
    import altair as alt
    cycles_df_reset = cycles_df.reset_index().melt(id_vars='Date', value_vars=['Cook Cycles', 'Pressure Cycles'], var_name='Cycle Type', value_name='Count')
    chart = alt.Chart(cycles_df_reset).mark_bar().encode(
        x=alt.X('Date:N', title='Date'),
        y=alt.Y('Count:Q', title='Count', stack='zero'),
        color='Cycle Type:N',
        column=alt.Column('Cycle Type:N', title='Cycle Type')
    ).properties(title='Cook and Pressure Cycles Per Day')
    st.altair_chart(chart, use_container_width=True)

