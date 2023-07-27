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
app.layout=html.Div('hi')

if __name__ == '__main__':
    app.run(debug=True)
