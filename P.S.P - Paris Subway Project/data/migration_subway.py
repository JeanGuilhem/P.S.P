

from grakn.client import GraknClient
import csv


#######################################################################################################################################
# 
#                                                   CHARGEMENT DES DONNEES  
#                                                      
#######################################################################################################################################

def build_vente_graph(inputs):
    with GraknClient(uri="localhost:48555") as client:
        with client.session(keyspace = "paris_subway") as session:
            liste_station = []
            for input in inputs:
                print("Loading from [" + input["data_path"] + "] into Grakn ...")

                #On veut faire en sorte d'append qu'une seule fois la station dans la db Grakn 
                #Du coup on doit prévoir le cas où la station a été ajoutée avant.
                #Ex: Si Chatelet a été append via le fichier de la ligne 7, la station en sera pas append dans la db par le fichier de la ligne 14.
                
                liste_fichier = ["./data_metro_14","./data_metro_13","./data_metro_12","./data_metro_11","./data_metro_10","./data_metro_9","./data_metro_8","./data_metro_7","./data_metro_6","./data_metro_5","./data_metro_4","./data_metro_3","./data_metro_2","./data_metro_1","./data_metro_7b","./data_metro_M3bis"]
                if input["data_path"]  in liste_fichier : 
                    load_data_into_grakn(input, session,liste_station)
                else : 
                    load_data_into_grakn2(input, session)


def load_data_into_grakn(input, session,liste_station):
    items = parse_data_to_dictionaries(input)
    for item in items:
        with session.transaction().write() as transaction:
            graql_insert_query = input["template"](item)
            name = graql_insert_query[1]
            if name not in liste_station:
                liste_station.append(name)
                print("Executing Graql Query: " + graql_insert_query[0])
                    
                transaction.query(graql_insert_query[0])
                transaction.commit()


    print("\nInserted " + str(len(items)) + " items from [ " + input["data_path"] + "] into Grakn.\n")




def load_data_into_grakn2(input, session):
    items = parse_data_to_dictionaries(input)
    for item in items:
        with session.transaction().write() as transaction:
            graql_insert_query = input["template"](item)
            print("Executing Graql Query: " + graql_insert_query)
                    
            transaction.query(graql_insert_query)
            transaction.commit()


    print("\nInserted " + str(len(items)) + " items from [ " + input["data_path"] + "] into Grakn.\n")


#Ajout de la relation qui manque après l'importation de toutes les données entre les stations Argentine et Charles de Gaulle Etoile
def ajout_relation() :
    with GraknClient(uri="localhost:48555") as client:
        with client.session(keyspace = "paris_subway") as session:
            with session.transaction().write() as transaction:
                graql_insert_query = ' match $station1 isa station, has name "Argentine"; $station2 isa station, has name "Charles De Gaulle Etoile"; insert $new-route (beginning : $station1, end : $station2 ) isa route, has station_ligne "M1";'
                transaction.query(graql_insert_query)
                transaction.commit()

#######################################################################################################################################
# 
#                                              QUERIES ASSIOCEES A SON ENTITE
#                                                                                                          
#######################################################################################################################################



def station_template(station):

    name = station["name"]
    lat = station["lat"]
    lon = station["lon"]

    graql_insert_query = 'insert $station isa station, has station_id "' + station["station_id"] + '"'
    graql_insert_query += ', has name "' + station["name"] + '"'
    graql_insert_query += ', has lat ' + lat
    graql_insert_query += ', has lon ' + lon
    graql_insert_query += ";"

    return graql_insert_query,name




def relation_route(tunnel) :

    beginning = tunnel["origin"]
    end = tunnel["destination"]

    graql_insert_query = 'match $station1 isa station, has name "'+beginning+'"; $station2 isa station, has name "'+end+'";'
    graql_insert_query += ' insert $new-route (beginning : $station1, end: $station2) isa route, has station_ligne "'+ tunnel["station_ligne"]+'";'

    return graql_insert_query

    



#######################################################################################################################################
# 
#                                           TRANSFORMATION EN DICTIONNAIRE DEPUIS UN CSV 
#                                                      
#######################################################################################################################################


def parse_data_to_dictionaries(input):
    items = []
    with open(input["data_path"] + ".csv") as data:
        for row in csv.DictReader(data, skipinitialspace = True):
            item = { key: value for key, value in row.items() }
            items.append(item)
    return items





#######################################################################################################################################
# 
#                                               SEQUENCE DE CREATION DE GRAPHE
#                                                                                                          
#######################################################################################################################################

station_liste = []

inputs = [
    {
        "data_path": "./data_metro_1",
        "template": station_template,
    },
        {
        "data_path": "./data_metro_2",
        "template": station_template,
    },
        {
        "data_path": "./data_metro_3",
        "template": station_template,
    },
        {
        "data_path": "./data_metro_4",
        "template": station_template,
    },
        {
        "data_path": "./data_metro_5",
        "template": station_template,
    },
        {
        "data_path": "./data_metro_6",
        "template": station_template,
    },
        {
        "data_path": "./data_metro_7",
        "template": station_template,
    },
        {
        "data_path": "./data_metro_7b",
        "template": station_template,
    },
        {
        "data_path": "./data_metro_8",
        "template": station_template,
    },
        {
        "data_path": "./data_metro_9",
        "template": station_template,
    },
        {
        "data_path": "./data_metro_10",
        "template": station_template,
    },
        {
        "data_path": "./data_metro_11",
        "template": station_template,
    },
        {
        "data_path": "./data_metro_12",
        "template": station_template,
    },
        {
        "data_path": "./data_metro_13",
        "template": station_template,
    },
        {
        "data_path": "./data_metro_14",
        "template": station_template,
    },
        {
        "data_path": "./data_metro_M3bis",
        "template": station_template,
    },  
    {
        "data_path": "./data_metro_MARKII_1",
        "template": relation_route,
    },
        {
        "data_path": "./data_metro_MARKII_2",
        "template": relation_route,
    },
        {
        "data_path": "./data_metro_MARKII_3",
        "template": relation_route,
    },
        {
        "data_path": "./data_metro_MARKII_4",
        "template": relation_route,
    },
        {
        "data_path": "./data_metro_MARKII_5",
        "template": relation_route,
    },
        {
        "data_path": "./data_metro_MARKII_6",
        "template": relation_route,
    },
        {
        "data_path": "./data_metro_MARKII_7",
        "template": relation_route,
    },
        {
        "data_path": "./data_metro_MARKII_8",
        "template": relation_route,
    },
        {
        "data_path": "./data_metro_MARKII_9",
        "template": relation_route,
    },
        {
        "data_path": "./data_metro_MARKII_10",
        "template": relation_route,
    },
        {
        "data_path": "./data_metro_MARKII_11",
        "template": relation_route,
    },
        {
        "data_path": "./data_metro_MARKII_12",
        "template": relation_route,
    },
        {
        "data_path": "./data_metro_MARKII_13",
        "template": relation_route,
    },
        {
        "data_path": "./data_metro_MARKII_14",
        "template": relation_route,
    },
        {
        "data_path": "./data_metro_MARKII_7 bis",
        "template": relation_route,
    },
        {
        "data_path": "./data_metro_MARKII_3 bis",
        "template": relation_route,
    },
]

build_vente_graph(inputs)

#On ajoute la relation qui manque entre les stations Charles de Gaulle Etoile et Argentine
ajout_relation()
