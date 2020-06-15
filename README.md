# P.S.P
Paris Subway Project  Drawing a map of the Paris's subway. From line 1 to line 14. All the data has been imported from csv file to a Grakn database and has been requested from it.

## Prerequisites

Python >= 3.6 

GraknClient

tkinter

This project works with Grakn 1.7.0

## Quickstart

- Install Grakn : https://dev.grakn.ai/docs/running-grakn/install-and-run
- Install Grakn Workbase ( not required but usefull and easier to navigate ) : https://grakn.ai/download#workbase
- Launch the Grakn server ( `grakn server start` ) 
- Create the P.S.P Grakn keyspace (via Workspace or console) : `paris_subway`
- Load the schema into the keyspace : `grakn console --keyspace paris_subway  --file schema/schema_subway.gql`
- Load the data into the db by launching the file `migration_subway.py` into `P.S.P/data`
- Launch the file `app.py` in order to get the map
- Launche the file `statistics.py` in order to interact with the data via the console


## Download Data

- I downloaded the stations data from the RATP: https://data.iledefrance-mobilites.fr/explore/dataset/emplacement-des-gares-idf/export/
- I created a csv the data for the lines relation here : https://gist.githubusercontent.com/NaPs/25309/raw/6cbcf7995d49bbf61d2dc7b4bc7dc426bbd3d6d1/paris.gph

You can have access to the code that I used to create all the `data_metro` or `data_metro_MARKII` csv in the file `download_data.py`

But I had to modify a larg ammount of data by hands in order to obtain the perfect data needed. So you will have to do the same if you want to restart all the project from zero. 

Pro tips : just use the final csv files.

## Data

There are two type of csv files : 

- `data_metro_{tube_line_name}.csv` contains all necessary data for a station from the `{tube_line_name}`

station_id [string] : the id of the stations ( not the Grakn id but the id from the RATP ) Ex: "612"
name [string] : the name of the station Ex: "Cambronne"
station_ligne [string] : the name of the line (from 1 to 14 for the Paris subway) Ex: "2"
lat [float] : the latitude gps coordinates for the station Ex: 48.5621
lon [float] : the longitude gps coordinates for the station Ex: 2.2951

- `data_metro_MARKII_{tube_line_name}.csv` contains the relation betweens station from the line `{tube_line_name}`

station_ligne [string] : the line name Ex: "M1"
origin [string] : the name of the origin station Ex: "La Defense"
destination [string] : the name of the destination station Ex: "Esplanade de la Defense"


