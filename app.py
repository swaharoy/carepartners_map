# old imports
import pandas as pd
from dash import Dash, dcc, html, Input, Output

import plotly.express as px
import numpy as np
import math
import json

# new imports
import os
from dotenv import load_dotenv 
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

import base64
import datetime
import io
from dash import dash_table, State, callback

### MongoDB
# access MongoDB Atlas cluster0
load_dotenv()
connection_string: str = os.environ.get('CONNECTION_STRING')
mongo_client: MongoClient = MongoClient(connection_string)

# add database and collection from Atlas 
database: Database = mongo_client.get_database('carepartners')
collection_dd: Collection = database.get_collection('donordata')
collection_pd: Collection = database.get_collection('programdata')

#collection_dd.delete_many({})

# create documents
def parse_upload(contents, filename, dstype):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            df = pd.read_csv(
                io.StringIO(decoded.decode('utf-8')))
            if any(df.columns.str.contains('unnamed',case = False)):
                df = pd.read_csv(io.BytesIO(decoded), skiprows=[0])
        elif 'xls' in filename:
            df = pd.read_excel(io.BytesIO(decoded))
            if any(df.columns.str.contains('unnamed',case = False)):
                df = pd.read_excel(io.BytesIO(decoded), skiprows=[0])
        else:
            return 'Please upload .xlsx or .csv file.'
    except Exception as e:
        print(e)
        return 'There was an error processing this file.'
    
    valid = valid_dataset(df, dstype)

    if valid:
        date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        store_data(dstype, content_string, date, filename)   
        return 'File successfully uploaded.'
    else:
        return 'The file does not contain the correct data fields.'

def valid_dataset(df, dstype):
    if (dstype == 'upload-data-dd'):
        return all([item in df.columns for item in ['Donor ID', 'Zip/Postal', 'Donor Type', 'Flags', 'Date', 'Gift Amount']])
    else: 
        return all([item in df.columns for item in ['Activity Type', 'Postal Code']])

def store_data (dstype, content, date, filename):   
    ddataset = {'time': date, 'filename': filename, 'data': content}

    if(type == 'upload-data-dd'):
        collection_dd.insert_one(ddataset)
    else:
        collection_pd.insert_one(ddataset)

def create_options(dstype):

    if(dstype == 'select-dd'):
        doc_list = list(collection_dd.find({}))
    elif(dstype == 'select-pd'):
        doc_list = list(collection_pd.find({}))

    new_options = []
    for i in range(len(doc_list)):
        ts = doc_list[i]['time']
        new_options.append({'label': ts, 'value':ts})

    return new_options

def decode_df(dstype, ts):

    if(dstype == 'select-dd'):
        doc = collection_dd.find_one({'time': ts})
    elif(dstype == 'select-pd'):
        doc = collection_pd.find_one({'time': ts})
    
    filename = doc['filename']
    content_string = doc['data']
    decoded = base64.b64decode(content_string)
    
    try:
        if 'csv' in filename:
            df = pd.read_csv(
                io.StringIO(decoded.decode('utf-8')))
            if any(df.columns.str.contains('unnamed',case = False)):
                df = pd.read_csv(io.BytesIO(decoded), skiprows=[0])
        elif 'xls' in filename:
            df = pd.read_excel(io.BytesIO(decoded))
            if any(df.columns.str.contains('unnamed',case = False)):
                df = pd.read_excel(io.BytesIO(decoded), skiprows=[0])
    except Exception as e:
        print(e)
        if(dstype == 'select-dd'):
            df = df_clean
        elif(dstype == 'select-pd'):
            df = df_clean2
    
    return df

### Layer 1
def clean_data(df):
    dfc = df.copy()

    #Rename columns
    dfc.columns = dfc.columns.str.replace(' ', '_')
    dfc.columns = [x.lower() for x in dfc.columns]
    dfc = dfc.rename(columns={'zip/postal': 'zip'})
    dfc = dfc.rename(columns={'date': 'year'})

    #Change data types
    dfc['year'] = dfc['year'].apply(lambda x: x.year)
    dfc['gift_amount'] = dfc['gift_amount'].apply(lambda x: x.replace('$','').replace(',','')).astype(float)

    #Clean zip codes
    dfc = dfc.dropna(subset=['zip'])
    dfc['zip'] = dfc['zip'].astype(str).apply(lambda x: x[:5])
    dfc = dfc[pd.to_numeric(dfc['zip'], errors='coerce').notnull()]
    dfc['zip'] = dfc['zip'].astype(str)

    #Clean flags
    dfc.loc[dfc['flags'].str.contains('BD', na=False), 'flags'] = 'BD'
    dfc.loc[dfc['flags'].str.contains('CLIENT', na=False), 'flags'] = 'CLIENT'
    dfc.loc[dfc['flags'].str.contains('VOL', na=False), 'flags'] = 'VOL'

   #MG Donors
    dfc['total_donor_gift'] = dfc.groupby('donor_id', sort=False)['gift_amount'].transform('sum')
    dfc['donor_level'] = dfc['total_donor_gift'].apply(lambda x: 'SG' if x <1000 else 'MG')
    dfc['donor_level'].values[dfc['total_donor_gift'].values >= 10000] = 'TG'

    return dfc

# filter years (range)
def filter_years(df_clean, start_year, end_year):
    df_year = df_clean.copy()
    df_year = df_year.loc[df_year['year'] >= start_year]
    df_year = df_year.loc[df_year['year'] <= end_year]

    return df_year

# filter donor type (multi-select)
def filter_type(df_clean, dtype):
    df_type = df_clean.copy()
    df_type = df_type.loc[df_type['donor_type'].isin(dtype)]
    return df_type

# filter donor flag (multi-select)
def filter_flag(df_clean, flag):
    df_flag = df_clean.copy()
    df_flag = df_flag.loc[df_flag['flags'].isin(flag)]
    return df_flag

# filter donor level (multi-select)
def filter_level(df_clean, level):
    df_level = df_clean.copy()
    df_level = df_level.loc[df_level['donor_level'].isin(level)]
    return df_level

# calc choropleth variables, drop duplicate zip codes
def choropleth_vars(df_filtered):
        df_cv = df_filtered.copy()
        
        df_cv['total_gift'] = df_cv.groupby('zip', sort=False)['gift_amount'].transform('sum')

        df_cv = df_cv.drop_duplicates(subset=['donor_id'])
        df_cv['total_donors'] = df_cv.groupby('zip', sort=False)['donor_id'].transform('count')

        df_cv = df_cv.loc[df_cv['total_gift'] > 0]
        df_cv = df_cv.drop_duplicates(subset=['zip'])

        df_cv['total_donors_format'] = df_cv['total_donors'].apply(lambda x: f'{x:,}')
        df_cv['total_gift_format'] = df_cv['total_gift'].apply(lambda x: math.trunc(x)).apply(lambda x: f'{x:,}')

        return df_cv

### Layer 2
def clean_data2(df):
    dfc = df.copy()

    #Rename columns
    dfc.columns = dfc.columns.str.replace(' ', '_')
    dfc.columns = [x.lower() for x in dfc.columns]
    dfc = dfc.rename(columns={'postal_code': 'zip'})

    #Clean Zip
    dfc = dfc.dropna(subset=['zip'])
    dfc['zip'] = dfc['zip'].astype(str).apply(lambda x: x[:5])

    #Group
    dfc['volunteers'] = dfc.groupby('zip', sort=False)['activity_type'].transform('count')
    dfc = dfc.drop_duplicates(subset=['zip'])

    #Add lat + long
    dfc = dfc.set_index('zip', drop=False)

    for i in range(len(zipcodes['features'])):
        zipcode = zipcodes['features'][i]['properties']['ZCTA5CE10']
        if zipcode in dfc['zip'].unique():
            dfc.loc[zipcode, 'lat'] = zipcodes['features'][i]['properties']['INTPTLAT10']
            dfc.loc[zipcode, 'long'] = zipcodes['features'][i]['properties']['INTPTLON10']

    dfc = dfc.dropna(subset=['lat'])
    dfc = dfc.dropna(subset=['long'])

    dfc['lat'] = dfc['lat'].astype(float)
    dfc['long'] = dfc['long'].astype(float)

    return dfc

### Display Map 
with open('data/txzipgeo.min.json') as zip:
  zipcodes = json.load(zip)

def display_choropleth(df_filtered, color_var, color_mode, color_scale, df_clean2, show):  
    
    df_zip = choropleth_vars(df_filtered)
    
    try:
        outlier = np.percentile(df_zip[color_var], [2, 98])
    except:
        outlier = [df_zip[color_var].min(), df_zip[color_var].max()]

    label = {'total_gift': 'Donation Amount', 'total_donors': 'Number of Donors'}

    fig = px.choropleth_mapbox(
        df_zip, geojson=zipcodes, locations='zip', color=color_var,
        color_continuous_scale=color_scale, range_color=[outlier[0],outlier[1]],
        mapbox_style=color_mode,
        zoom=8, center = {"lat": 29.749907, "lon": 	-95.358421},
        opacity=0.65,featureidkey="properties.ZCTA5CE10", custom_data=['zip', df_zip['total_gift_format'], df_zip['total_donors_format']]
        )
    
    fig.update_layout(
        margin={"r":0,"t":0,"l":0,"b":0},
        hoverlabel={
            "bgcolor":"white",
            "font_size" : 16,
            },
        )
    
    fig.update_traces(hovertemplate=
                    "<b>%{customdata[0]}</b><br>" +
                    "Total Donations: $%{customdata[1]}<br>" +
                    "Total Donors: %{customdata[2]}"+
                    "<extra></extra>"
                    )
    
    if(show):
        fig.add_scattermapbox(
            lat=df_clean2['lat'],
            lon=df_clean2['long'],
            hoverinfo='skip',
            hovertemplate=None,
            marker={"color": "#90C2E7"}
        )

    fig.update_mapboxes(
        bounds={
            "east": -87,
            "north": 45,
            "south": 20,
            "west": -112
        }
    )

    fig.update_coloraxes(colorbar_title_text=label[color_var])
    
    return fig

df_og = decode_df('select-dd', 'Original Data Set (7/10/23)')
df_clean = clean_data(df_og.copy())

df_og2 = decode_df('select-pd', 'Original Data Set (7/18/23)')
df_clean2 = clean_data2(df_og2.copy())

### App
# instantiate app
app = Dash(__name__)

# create app layout
app.layout=html.Div(
                className = "bodyContainer",
                children =[
                        html.Div(
                            className = "contentContainer",
                            children= [
                                html.Div(
                                    className ='titleContainer', 
                                    children=[
                                        html.Div(
                                            className = 'title',
                                            children = 'CarePartners Donors'),
                                        html.Div(
                                            className = 'subtitle',
                                            children = 'an interactive map')
                                    ]
                                ),
                                html.Div(
                                    className ='section', 
                                    id = 'graphContainer',
                                    children=[
                                            dcc.Graph(
                                        id="graph", 
                                        responsive=True,
                                        figure = display_choropleth(df_clean, 'total_gift', 'carto-positron', 'Darkmint',df_clean2, True))
                                    ]
                                )
                            ]
                        ),
                        html.Div(
                            className = "sidebarContainer",
                            children =[
                                html.Div(
                                    className ='section selectorContainer', 
                                    children=[
                                        html.Div(
                                            id ='color-scale-var', 
                                            children=[
                                                html.Div(
                                                    className="selector-label",
                                                    children='Color Scale Variable'
                                                ),
                                                dcc.Dropdown(
                                                    options=[ 
                                                        {'label': 'Donation Amount', 'value': 'total_gift'},
                                                        {'label': 'Number of Donors', 'value': 'total_donors'},
                                                        ],
                                                    value = "total_gift",
                                                    placeholder ='Select color variable..',
                                                    id = "color-var",
                                                )
                                            ]
                                        ),
                                            html.Div(
                                                id ='year-range', 
                                                children=[
                                                    html.Div(
                                                        className="selector-label",
                                                        children='Year Range'
                                                    ),
                                                    html.Div(
                                                        id = 'year-range-dropdowns',
                                                        children = [
                                                            dcc.Dropdown(
                                                                options=[{'label':x, 'value': x} for x in range(df_clean['year'].min(), df_clean['year'].max())],
                                                                value = df_clean['year'].min(),
                                                                placeholder ='Start year...',
                                                                className = "dropdown",
                                                                id='year-start'
                                                            ),
                                                            dcc.Dropdown(
                                                                options=[{'label':x, 'value': x} for x in range(df_clean['year'].min(), df_clean['year'].max() + 1)],
                                                                value = df_clean['year'].max(),
                                                                placeholder ='End year...',
                                                                id='year-end'
                                                            )
                                                        ]
                                                    ) 
                                                ]
                                            ),
                                            html.Div(
                                                id ='donor-filters', 
                                                children=[
                                                    html.Div(
                                                        className="selector-label info-label",
                                                        children=['Filter By Donors', 
                                                                html.Div(
                                                                        html.Img(src='assets/info.svg'),
                                                                        id = 'info',
                                                                        )]
                                                    ),
                                                                html.Div(
                                                                    id='donor-filters-dropdowns',
                                                                    children =[
                                                                        dcc.Dropdown(
                                                                            options=[ 
                                                                                    {'label': 'Business', 'value': 'BU'},
                                                                                    {'label': 'Congregation', 'value': 'CON'},
                                                                                    {'label': 'Foundation', 'value': 'FN'},
                                                                                    {'label': 'Government', 'value': 'GV'},
                                                                                    {'label': 'Individual', 'value': 'IN'},
                                                                                    {'label': 'Organization-Non-Profit', 'value': 'OR'}
                                                                                    ],
                                                                            value = [],
                                                                            multi = True,
                                                                            placeholder ='Donor type...',
                                                                            id = "donor-type"
                                                                        ),
                                                                        dcc.Dropdown(
                                                                            options=[
                                                                                    {'label': 'Board Member', 'value': 'BD'},
                                                                                    {'label': 'Client', 'value': 'CLIENT'},
                                                                                    {'label': 'Volunteer', 'value': 'VOL'}],
                                                                            value = [],
                                                                            multi = True,
                                                                            placeholder ='Donor flag...',
                                                                            id = "donor-flag"
                                                                        ),
                                                                        dcc.Dropdown(
                                                                                options=[
                                                                                        {'label': 'Small Gifts (<$1,000)', 'value': 'SG'},
                                                                                        {'label': 'Major Gifts ($1,000 - $10,000)', 'value': 'MG'},
                                                                                        {'label': '$10,000+ Gifts', 'value': 'TG'}],
                                                                                value = [],
                                                                                multi = True,
                                                                                placeholder ='Donor level...',
                                                                                id = "donor-level")
                                                                        ]
                                                                    ) 
                                                    ]
                                            ),
                                            html.Div(
                                                id ='style-graph', 
                                                children=[
                                                    html.Div(
                                                        className="selector-label",
                                                        id="style-graph-label",
                                                        children=['Style Graph',
                                                                dcc.Checklist(
                                                                    options=['Show program locations.'],
                                                                    value=['Show program locations.'],
                                                                    id='show')
                                                        ]
                                                    ),          
                                                    html.Div(
                                                        id='style-graph-dropdowns',
                                                        children =[
                                                            dcc.Dropdown(
                                                                options=[
                                                                        {'label': 'Light Mode', 'value': 'carto-positron'}, 
                                                                        {'label': 'Dark Mode', 'value': 'carto-darkmatter'}  
                                                                        ],
                                                                value = "carto-positron",
                                                                placeholder ='Base map color...',
                                                                id = "color-mode"
                                                            ),
                                                            dcc.Dropdown(
                                                                options=[ {'label': 'Dark Mint Green', 'value': 'Darkmint'},
                                                                        {'label': 'Sunset', 'value': 'Sunsetdark'},
                                                                        {'label': 'Yellow/Blue', 'value': 'Cividis_r'},
                                                                        {'label': 'Purple/Blue/Green', 'value': 'PuBuGn'},
                                                                        ],
                                                                value = "Darkmint",
                                                                placeholder ='Color scale...',
                                                                id = "color-scale"
                                                            )
                                                        ]
                                                    )
                                                ]
                                            )
                                    ]
                ),
                                html.Div(
                                    className ='section upload-container', 
                                    children=[
                                        html.Div(
                                            className="selector-label info-label",
                                            children=['Upload donor data.', 
                                                html.Div(
                                                        html.Img(src='assets/info.svg'),
                                                        id = 'info-dd',
                                                        )]
                                        ),
                                        dcc.Dropdown(
                                                    options=[],
                                                    placeholder ='Select donor data set...',
                                                    id = "select-dd",
                                                ),
                                        dcc.Upload(
                                            className='upload-data',
                                            id='upload-data-dd',
                                            children=html.Div([
                                                'Drag and Drop or ',
                                                html.A('Select Files')
                                            ])
                                        ),
                                        html.Div(
                                            id="error-div-dd",
                                            children = ''
                                        ),
                                        html.Div(
                                            className="selector-label info-label",
                                            children=['Upload program data.', 
                                                    html.Div(
                                                            html.Img(src='assets/info.svg'),
                                                            id = 'info-pd',
                                                            )]
                                        ),
                                        dcc.Dropdown(
                                                    options=[],
                                                    placeholder ='Select donor data set...',
                                                    id = "select-pd",
                                                ),
                                        dcc.Upload(
                                            className='upload-data',
                                            id='upload-data-pd',
                                            children=html.Div([
                                                'Drag and Drop or ',
                                                html.A('Select Files')
                                            ])
                                        ),
                                        html.Div(
                                            id="error-div-pd",
                                            children = ''
                                        )
                                    ]
                                )
                            ]
                )
            ]
        )

@callback(
    Output('error-div-dd', 'children'),
    Output('select-dd', 'options'),
    Input('upload-data-dd', 'contents'),
    State('upload-data-dd', 'filename'))
def update_output_dd(content, name):
    if content is not None:
        children = parse_upload(content, name, 'upload-data-dd')
    else:
        children = None
   
    options = create_options('select-dd')

    return (children, options)

@callback(
    Output('error-div-pd', 'children'),
    Output('select-pd', 'options'),
    Input('upload-data-pd', 'contents'),
    State('upload-data-pd', 'filename'))
def update_output_dd(content, name):
    if content is not None:
        children = parse_upload(content, name, 'upload-data-pd')
    else:
        children = None
   
    options = create_options('select-pd')

    return (children, options)  


    
@callback(
    Output('graph', 'figure'),
    Input('color-var', 'value'),
    Input('year-start', 'value'),
    Input('year-end', 'value'),
    Input('donor-type', 'value'),
    Input('donor-flag', 'value'),
    Input('donor-level', 'value'),
    Input('color-mode', 'value'),
    Input('color-scale', 'value'),
    Input('show', 'value'),
    Input('select-dd', 'value'),
    Input('select-pd', 'value'))
def update_figure(color_var, start_year, end_year, donor_type, donor_flag, donor_level, color_mode, color_scale, show, select_dd, select_pd):

    df1 = df_clean
    df2 = df_clean2

    if select_dd != None:
        df1 = clean_data(decode_df('select-dd', select_dd).copy())
    if select_pd != None:
        df2 = clean_data2(decode_df('select-pd', select_pd).copy())

    df_filtered = filter_years(df1, start_year, end_year)

    if (0 < len(donor_type) < 6):
        df_filtered = filter_type(df_filtered, donor_type)

    if (0 < len(donor_flag) < 3):
        df_filtered = filter_flag(df_filtered, donor_flag)

    if (0 < len(donor_level) < 3):
        df_filtered = filter_level(df_filtered, donor_level)

    if('Show program locations.' in show):
        disp = True
    else:
        disp = False

    fig = display_choropleth(df_filtered, color_var, color_mode, color_scale, df2, disp)
    return fig

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000)

