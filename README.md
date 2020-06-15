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
