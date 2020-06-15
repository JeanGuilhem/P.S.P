import csv
import os
import geopy.distance

# ===============================================================================================


# write in a new csv file the data that matters to us (cad les stations de metro)
def write_interesseting_data(csvname_all_data):

    with open(csvname_all_data) as csvfile:

        spamreader=csv.reader(csvfile, delimiter=";")
        for row in spamreader:


            # row[13] == 1 -> la ligne correspond à une station de metro (et pas de bus ou tram)
            if(row[13] == '1'):


                # Ex : data_metro_1.csv -> data du metro ligne 1
                file_name="data_metro_{}.csv".format(row[26])

                with open(file_name, 'a') as csvfile2:


                    spamwriter=csv.writer(csvfile2)

                    # if the file is empty, we add this in the top of it :
                    if os.stat(file_name).st_size == 0:
                        spamwriter.writerow(
                            ['station_id', 'name', 'station_ligne', 'lat', 'lon'])


                    # id, nom, ligne, coordonees
                    list=(row[0].split(","))
                    name = supprime_accent(row[5]) #suppressions des accents -> faire correspondre les noms entre les fichiers de data
                    sep = '('
                    name = name.split(sep,1)[0]
                    print(f"From {row[5]} to {name}")
                    spamwriter.writerow(
                        (row[4], name, row[26], list[0], list[1]))

    print("Finishing creation of all lines data and creation of csv's")



def supprime_accent(ligne):
        """ supprime les accents du texte source """
        accents = { 'a': ['à', 'ã', 'á', 'â'],
                    'e': ['é', 'è', 'ê', 'ë'],
                    'E': ['É'],
                    'i': ['î', 'ï'],
                    'u': ['ù', 'ü', 'û'],
                    'o': ['ô', 'ö'] ,
                    ' ': ['-']
                    }
        for (char, accented_chars) in accents.items():
            for accented_char in accented_chars:
                ligne = ligne.replace(accented_char, char)
        return ligne



#Ecris les csv MARKII permettant la création des relations entre nos stations.
def just_tunnel(csv_file_name) :
    print("Openning "+ csv_file_name+" file...")
    with open(csv_file_name) as csvfile :
        
        spamreader = csv.reader(csvfile, delimiter=";")

        for row in spamreader : 

             
            print(row)
            name = row[0]
            file_name="data_metro_MARKII_{}.csv".format(name[1:])
            with open(file_name, 'a') as csvfile2:
                spamwriter=csv.writer(csvfile2)

                # if the file is empty, we add this in the top of it :
                if os.stat(file_name).st_size == 0:
                    spamwriter.writerow(['station_ligne', 'origin', 'destination'])

                # id, nom, ligne, coordonees
                spamwriter.writerow((row[0], row[1], row[2]))
        print("Finishing collecting data for line "+ row[0])





# ============================================EXECUTION================================================================

csvname_all_data="emplacement-des-gares-idf.csv"


#Création des fichiers des stations de metro par ligne (Ex: data_metro_3.csv)
write_interesseting_data(csvname_all_data)


#création des fichiers des tunnels de metro par ligne sans les coordonées géographiques (Ex: data_metro_MARKII_3.csv)
just_tunnel('tunnel_file.csv')

