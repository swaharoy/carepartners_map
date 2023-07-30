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

# create/get documents
def parse_upload(contents, filename, type):
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
            return html.Div([
                'Please upload .xlsx or .csv file.'
            ])
    except Exception as e:
        print(e)
        return html.Div([
            'There was an error processing this file.'
        ])
    
    #TODO: style error message
    if valid_dataset(df, type) == False:
                return html.Div([
                    'The file does not contain the correct data fields'])
    else:
        store_data(type, content_string)
    
    return None

def valid_dataset(df, type):
    if (type == 'upload-data-dd'):
        return all([item in df.columns for item in ['Donor ID', 'Zip/Postal', 'Donor Type', 'Flags', 'Date', 'Gift Amount']])
    else: 
        return all([item in df.columns for item in ['Activity Type', 'Postal Code']])

def store_data (type, content):   
    ddataset = {'time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'data': content}

    if(type == 'upload-data-dd'):
        collection_dd.insert_one(ddataset)
    else:
        collection_pd.insert_one(ddataset)

### Layer 1


### App
# instantiate app
app = Dash(__name__)

# create app layout
app.layout=html.Div(
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

@callback(Output('error-div-dd', 'children'),
              Input('upload-data-dd', 'contents'),
              State('upload-data-dd', 'filename'))
def update_output_dd(content, name):
    if content is not None:
        children = [parse_upload(content, name, 'upload-data-dd')]
        return children
    
@callback(Output('error-div-pd', 'children'),
              Input('upload-data-pd', 'contents'),
              State('upload-data-pd', 'filename'))
def update_output_pd(content, name):
    if content is not None:
        children = [parse_upload(content, name, 'upload-data-pd')]
        return children

if __name__ == '__main__':
    app.run(debug=True)

