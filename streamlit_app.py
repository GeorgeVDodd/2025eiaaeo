import streamlit as st
import pandas as pd
import math
from pathlib import Path
import requests
import pandas as pd
import time # Import the time module
import pandas as pd
import io as io# Needed for StringIO

# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title='2025 Annual Energy Outlook',
    page_icon=':earth_americas:', # This is an emoji shortcode. Could be a URL too.
)

# -----------------------------------------------------------------------------
# Declare some useful functions.

@st.cache_data(show_spinner=True)
def get_power_data():
    egrid_ferc_mapping = """eGRID Subregion(s),NERC/ISO Subregion,Subregion Name,regionId,Code
AZNM,SRSG,Western Electricity Coordinating Council / Southwest,5-13,weccsw
CAMX,CANO,Western Electricity Coordinating Council / California North,5-21,wecccan
CAMX,CASO,Western Electricity Coordinating Council / California South,5-22,wecccas
ERCT,TRE,Texas Reliability Entity,5-1,tre
FRCC,FRCC,Florida Reliability Coordinating Council,5-2,flrc
MROE,MISE,Midcontinent / East,5-5,mce
MROW,MISW,Midcontinent / West,5-3,mcw
NEWE,ISNE,Northeast Power Coordinating Council / New England,5-7,npccne
NWPP,NWPP,Western Electricity Coordinating Council / Northwest Power Pool Area,5-23,wenwpp
NWPP,BASN,Western Electricity Coordinating Council / Basin,5-25,wenwpp
NYCW,NYCW,Northeast Power Coordinating Council / New York City and Long Island,5-8,nenycli
NYUP,NYUP,Northeast Power Coordinating Council / Upstate New York,5-9,npccupy
NYLI,NYCW,Northeast Power Coordinating Council / New York City and Long Island,5-8,nenycli
RFCE,PJME,PJM / East,5-10,pjme
RFCM,MISE,Midcontinent / East,5-5,pjmw
RFCW,PJMW,PJM / West,5-11,pjmw
RFCW,PJMC,PJM / Commonwealth Edison,5-12,pjmce
RFCW,MISC,Midcontinent / Central,5-4,pjmw
SRMW,MISC,Midcontinent / Central,5-4,mcc
RMPA,RMRG,Western Electricity Coordinating Rockies,5-24,weccrks
SPNO,SPPC,Southwest Power Pool / Central,5-18,swppc
SPNO,SPPN,Southwest Power Pool / North,5-19,swppno
SPSO,SPPS,Southwest Power Pool / South,5-17,swppso
SRMV,MISS,Midcontinent / South,5-6,mcs
SRSO,SRSE,SERC Reliability Corporation / Southeastern,5-16,sercsoes
SRTV,SRCE,SERC Reliability Corporation / East,5-14,serce
SRVC,PJMD,PJM / Dominion,5-13,pjmd
SRVC,SRCA,SERC Reliability Corporation / South,5-16,serccnt
"""

    egrid_ferc_mapping_df = pd.read_csv(io.StringIO(egrid_ferc_mapping))
    # You don't need reset_index() unless you explicitly want the index as a column
    egrid_ferc_mapping_df = egrid_ferc_mapping_df.rename(columns={"Code": "regionCode"})

    all_data = []

    for code in egrid_ferc_mapping_df["regionCode"].dropna().unique():
        url = (
            "https://api.eia.gov/v2/aeo/2025/data/"
            f"?frequency=annual&data[0]=value"
            "&facets[scenario][]=ref2025"
            f"&facets[seriesId][]=prce_NA_comm_NA_elc_NA_{code}_ncntpkwh"
            "&sort[0][column]=scenario&sort[0][direction]=desc"
            "&sort[1][column]=value&sort[1][direction]=asc"
            "&offset=0&length=5000"
            "&api_key=1DKoondB9fYm25utsytvlwoIweRUF5devMPnMVwx"
        )

        time.sleep(0.25)  # be polite; 5 seconds per code is very slow unless you must throttle hard

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            json_data = response.json()
        except Exception as e:
            # record the failure but keep going
            all_data.append(
                {"regionCode": code, "seriesId": None, "period": None, "value": None, "error": str(e)}
            )
            continue

        data_rows = (json_data.get("response") or {}).get("data") or []
        if not data_rows:
            all_data.append({"regionCode": code, "seriesId": None, "period": None, "value": None})
            continue

        for item in data_rows:
            # Ensure seriesId exists and is safely splittable
            sid = item.get("seriesId")
            if isinstance(sid, str):
                parts = sid.split("_")
                # Your original code used [6]; this is safe-guarded now
                item["regionCode"] = parts[6] if len(parts) > 6 else code
            else:
                item["regionCode"] = code

            all_data.append(item)

    final_df = pd.DataFrame(all_data)

    e_grid_prices_df = pd.merge(
        final_df,
        egrid_ferc_mapping_df[["regionCode", "eGRID Subregion(s)"]],
        on="regionCode",
        how="left",
    )

    power_df = (
        e_grid_prices_df.assign(value=pd.to_numeric(e_grid_prices_df["value"], errors="coerce"))
        .groupby(["period", "scenario", "eGRID Subregion(s)", "unit"], dropna=False)["value"]
        .mean()
        .reset_index()
        .rename(columns={"value": "Average Value"})
    )

    return power_df


power_df = get_power_data()
#update formats 
power_df["period"] = (
    pd.to_datetime(power_df["period"], errors="coerce")
    .dt.year
    .astype("Int64")   # nullable integer (recommended)
)
#st.dataframe(power_df)
# -----------------------------------------------------------------------------
# Draw the actual page

# Set the title that appears at the top of the page.
'''
# :earth_americas: 2025 Annual Energy Outlook 

Browse EIA Power Data from the 2025 Annual Energy Outlook.
'''

# Add some spacing
''
''
with st.container(border=True):
    #create date range for the slider filters
    min_value = power_df['period'].min()
    max_value = power_df['period'].max()
    #create the eGridRegions list for the multiselect filter
    eGridRegions = power_df['eGRID Subregion(s)'].unique().tolist()

    #Create the the slider 
    from_year, to_year = st.slider(
    'Which years are you interested in?',
        min_value=min_value,
        max_value=max_value,
        value=[min_value, max_value])

    if not len(eGridRegions):
        st.warning("Select at least one eGridRegion")

    selected_eGridRegions = st.multiselect(
        'Which eGrid regions would you like to view?',
        eGridRegions,
        ['AZNM', 'CAMX', 'ERCT', 'FRCC', 'MROE', 'MROW', 'NEWE'])  # Default selections

''
''
''


first_year = power_df[power_df['period'] == from_year]
last_year = power_df[power_df['period'] == to_year]

# Filter the data
filtered_power_df = power_df[
        (power_df['eGRID Subregion(s)'].isin(selected_eGridRegions))
        & (power_df['period'] <= to_year)
        & (from_year <= power_df['period'])
    ]

st.header('Power Price Projections', divider='gray')

''

#st.line_chart(
 #      filtered_power_df,
 #      x='period',
 #      y='Average Value',
 #      color='eGRID Subregion(s)',
 #   )

''
''


st.header(f'Power Prices in {to_year}', divider='gray')

tab1, tab2 = st.tabs(["Chart", "Dataframe"])
tab1.line_chart(filtered_power_df,         
        x='period',
        y='Average Value',
        color='eGRID Subregion(s)',
        height=250)
tab2.dataframe(filtered_power_df, height=250, use_container_width=True)