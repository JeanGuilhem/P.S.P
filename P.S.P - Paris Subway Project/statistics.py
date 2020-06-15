# Copyright 2020 Grakn Labs
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from grakn.client import GraknClient
import sys
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import time  


def print_to_log(title, content):
  print(title)
  print("")
  print(content)
  print("\n")


# How many stations do exist?
def query_station_count(question, transaction):
    print_to_log("Question: ", question)

    query = 'compute count in station;'

    print_to_log("Query:", query)

    answer = list(transaction.query(query))[0]
    number_of_stations = answer.number()

    print("Number of stations: " + str(number_of_stations))

    return number_of_stations


def correspondance(mot_a_comparer) :
    liste_station = []
    with GraknClient(uri="localhost:48555") as client:
        with client.session(keyspace="paris_subway") as session:
            with session.transaction().read() as transaction:
                
                query = 'match $sta isa station, has name $name;get $name;'
                origin_iterator = execute_and_log(query,transaction)
                for i in origin_iterator : 
                    name = i.get("name").value()
                    liste_station.append(name)
    
    correspondance = process.extract(mot_a_comparer,liste_station)
    corres = correspondance[0]
    corres = corres[0]
    return corres
                


# Which is the west most station in London?
def query_northernmost_station(question, transaction):
    print_to_log("Question: ", question)

    query = 'compute min of lat, in station;'

    print_to_log("Query:", query)

    answer = list(transaction.query(query))[0]
    lat = answer.number()

    query = [
        'match',
        '   $sta isa station, has lat $lat, has name $nam;',
        '   $lat ' + str(lat) + ';',
        'get $nam;'
    ]

    print_to_log("Query:", "\n".join(query))
    query = "".join(query)

    answers = [ans.get("nam") for ans in transaction.query(query)]
    result = [answer.value() for answer in answers]

    print_to_log("Northmost stations with " + str(lat) + " are: ", result)

    return [lat, result]


def execute_and_log(query, transaction):
    response = transaction.query(query)
    return response

# Give the shortest path between two stations
def query_path_between_stations(question, transaction) : 


    name11 = input("Rentrez le nom de la station d'origine : ")
    name22 = input("Rentrez le nom de la station d'arrivée : ")
    name1 = correspondance(name11)
    name2 = correspondance(name22)
    print("Correspondance dans la db : " + name11 + " -> " + name1)
    print("Correspondance dans la db : " + name22 + " -> " + name2)

    query = ' match $sta isa station, has name "' + name1 + '";get $sta;'
    origin_iterator = execute_and_log(query,transaction)
    for i in origin_iterator : 
        id1 = i.get("sta")
        id1 = id1.id
        print("ID de la station d'origine : " + id1)

    query = ' match $sta isa station, has name "' + name2 + '";get $sta;'
    origin_iterator = execute_and_log(query,transaction)
    for i in origin_iterator : 
        id2 = i.get("sta")
        id2 = id2.id
        print("ID de la station de destination : " + id2)

    tmps1=time.clock()

    print("Patientez pendant que je recherche un itinéraire...")
    shortest_path_ids = []
    query = 'compute path from ' + id1 + ', to ' + id2 + ';'
    shortest_path_concept_list = list(execute_and_log(query, transaction))[0]
    for shortest_path_node_id in shortest_path_concept_list.list():
                    concepts_list= list(transaction.query("match $sta id " + shortest_path_node_id + "; $sta has name $nam; get;"))
                    if len(concepts_list) > 0:
                        concept = concepts_list[0]
                        if concept.map().get("sta").type().label() == 'station':
                            shortest_path_ids.append(shortest_path_node_id)
    
    liste_name = []
    liste_ligne = []
    print("Nomnbre de stations à parcourir : " + f"{len(shortest_path_ids)}")
    for i in range(0,len(shortest_path_ids)) :
        query = 'match $sta id ' + shortest_path_ids[i] + ', has name $name;get $name;'
        if i+1 < len(shortest_path_ids) :
            id1 = shortest_path_ids[i]
            id2 = shortest_path_ids[i+1]
            query2 = ' match $sta1 id '+ id1 +'; $sta2 id '+id2+';  $route ($sta1 , $sta2 ) isa route, has station_ligne $ligne; get $ligne ;'
            iterator = execute_and_log(query2,transaction)
            for y in iterator :
                ligne = y.get('ligne').value()
                liste_ligne.append(ligne)
                

        origin_iterator = execute_and_log(query,transaction)
        for j in origin_iterator :
            name = j.get('name').value()
            print(name)
            sys.stdout.write('  |')
            total = len(liste_ligne)
            print("    "+liste_ligne[total-1])
            liste_name.append(name)
    tmps2=time.clock()
    print (f"Temps d'execution = {(tmps2-tmps1)} s")

    print("DESTINATION ATTEINTE")





def execute_query_all(transaction):
  for qs_func in query_examples:
    question = qs_func["question"]
    query_function = qs_func["query_function"]
    query_function(question, transaction)
    print("\n - - -  - - -  - - -  - - - \n")


query_examples = [
    {
        "question": "How many stations do exist?",
        "query_function": query_station_count
    },
    {
        "question": "Which is the northernmost station in Paris?",
        "query_function": query_northernmost_station
    },
    {
        "question": "Get a path between two stations",
        "query_function" : query_path_between_stations
    }
]

def init(qs_number):
    # create a transaction to talk to the keyspace
    with GraknClient(uri="localhost:48555") as client:
        with client.session(keyspace="paris_subway") as session:
            with session.transaction().read() as transaction:
                # execute the query for the selected question
                if qs_number == 0:
                    execute_query_all(transaction)
                else:
                    question = query_examples[qs_number - 1]["question"]
                    query_function = query_examples[qs_number - 1]["query_function"]
                    query_function(question, transaction)

if __name__ == "__main__":

    """
        The code below:
        - gets user's selection wrt the queries to be executed
        - creates a Grakn client > session > transaction connected to the keyspace
        - runs the right function based on the user's selection
        - closes the session and transaction
    """

    # ask user which question to execute the query for
    print("")
    print("For which of these questions, on the tube knowledge graph, do you want to execute the query?\n")
    for index, qs_func in enumerate(query_examples):
        print(str(index + 1) + ". " + qs_func["question"])
    print("")

    # get user's question selection
    qs_number = -1
    while qs_number < 0 or qs_number > len(query_examples):
        qs_number = int(input("choose a number (0 for to answer all questions): "))
    print("")

    init(qs_number)