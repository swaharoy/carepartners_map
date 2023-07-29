# old imports
import pandas as pd
from dash import Dash, dcc, html, Input, Output

import plotly.express as px
import numpy as np
import math
import json

# new imports
import bson 
import os
from dotenv import load_dotenv 
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

import base64
import datetime
import io
from dash import dash_table, State, callback

# access MongoDB Atlas cluster0
load_dotenv()
connection_string: str = os.environ.get('CONNECTION_STRING')
mongo_client: MongoClient = MongoClient(connection_string)

# add database and collection from Atlas 
database: Database = mongo_client.get_database('carepartners')
collection: Collection = database.get_collection('donordata')

ddataset = {'time': 3, 'data': 'base64 link blah blah'}
collection.insert_one(ddataset)

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
                                children=html.Div([
                                    'Drag and Drop or ',
                                    html.A('Select Files')
                                ])
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
                                children=html.Div([
                                    'Drag and Drop or ',
                                    html.A('Select Files')
                                ])
                            )
                        ]
                    )

#TODO: base64 --> error check + decode --> pandas df
#TODO:
#TODO: Read - from DB
#document schema: id, timestamp, base64 

def parse_contents(contents, filename, date):
    content_type, content_string = contents.split(',')

    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            # Assume that the user uploaded a CSV file
            df = pd.read_csv(
                io.StringIO(decoded.decode('utf-8')))
        elif 'xls' in filename:
            # Assume that the user uploaded an excel file
            df = pd.read_excel(io.BytesIO(decoded))
    except Exception as e:
        print(e)
        return html.Div([
            'There was an error processing this file.'
        ])

    return html.Div([
        html.H5(filename),
        html.H6(datetime.datetime.fromtimestamp(date)),

        dash_table.DataTable(
            df.to_dict('records'),
            [{'name': i, 'id': i} for i in df.columns]
        ),

        html.Hr(),  # horizontal line

        # For debugging, display the raw contents provided by the web browser
        html.Div('Raw Content'),
        html.Pre(contents[0:200] + '...', style={
            'whiteSpace': 'pre-wrap',
            'wordBreak': 'break-all'
        })
    ])

# @callback(Output('output-data-upload', 'children'),
#               Input('upload-data', 'contents'),
#               State('upload-data', 'filename'),
#               State('upload-data', 'last_modified'))
def update_output(list_of_contents, list_of_names, list_of_dates):
    if list_of_contents is not None:
        children = [
            parse_contents(c, n, d) for c, n, d in
            zip(list_of_contents, list_of_names, list_of_dates)]
        return children

if __name__ == '__main__':
    app.run(debug=True)

