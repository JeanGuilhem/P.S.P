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

from six.moves import tkinter as tk
from grakn.client import GraknClient
import datetime
import random
import geopy.distance
import sys


def transform_to_range(val, old_min, old_max, new_min, new_max):
    """
    Transform a value from an old range to a new range
    :return: scaled value
    """
    old_range = (old_max - old_min)
    new_range = (new_max - new_min)
    new_val = (((val - old_min) * new_range) / old_range) + new_min
    return new_val


def transform_coords(lon, lat, min_lon, max_lon, min_lat, max_lat, new_width, new_height):
    """
    Transforms grid coordinates to a coordinate system that can be easily rendered.
    :param lon: longitude of the coordinates to scale
    :param lat: latitude of the coordinates to scale
    :param min_lon: the minimum longitude, which will be mapped to x = 0
    :param max_lon: the maximum longitude, which will be mapped to x = new_width
    :param min_lat: the minimum latitude, which will be mapped to y = 0
    :param max_lat: the minimum latitude, which will be mapped to y = new_height
    :param new_width: the maximum height of the coordinates to map to
    :param new_height: the maximum width of the coordinates to map to
    :return:
    """
    lon = transform_to_range(lon, min_lon, max_lon, 0, new_width)
    lat = new_height - transform_to_range(lat, min_lat, max_lat, 0, new_height)
    return lon, lat


def _create_circle(self, x, y, r, **kwargs):
    """
    Helper function for easily drawing circles with tkinter, rather than ovals
    :param x: circle centre x-coordinate
    :param y: circle centre y-coordinate
    :param r: circle radius
    :param kwargs:
    :return:
    """
    return self.create_oval(x-r, y-r, x+r, y+r, **kwargs)


def execute_and_log(query, transaction):
    # print("\n" + ";\n".join(query.split(";")).replace("match", "match\n"))
    response = transaction.query(query)
    # print("... query complete.")
    return response


# Attach the circle helper function to tkinter so that we can use it more naturally
tk.Canvas.create_circle = _create_circle


class TubeGui:

    # Zoom attributes
    ZOOM_IN_SCALE = 2
    ZOOM_OUT_SCALE = 1/ZOOM_IN_SCALE

    # Size attributes
    SEINE_WIDTH = 10
    STATION_FONT_SIZE = 5
    STATION_CIRCLE_RADIUS = 3
    STATION_K_CORE_MAX_RADIUS = 15

    STATION_DEGREE_MAX_RADIUS = 17
    ROUTES_DEGREE_MAX_RADIUS = 8
    TUNNEL_SHORTEST_PATH_WIDTH = 20
    # Station connections
    LINE_WIDTH = 2
    LINE_SPACING = 0.5

    # Color attributes
    SEINE_COLOR = "#def"
    STATION_K_CORE_COLOUR = "#AAF"
    STATION_DEGREE_COLOUR = "#FF4821"
    TUNNEL_SHORTEST_PATH_COLOUR = "#DDD"

    # Hotkeys
    STATION_K_CORE_KEY = "k"
    STATION_ROUTE_KEY = "r"
    CLEAR_SHORTEST_PATH_KEY = "q"
    CLEAR_ALL_KEY = "c"

    # Used in calculating aspect ratio
    COMPUTE_MIN_LAT = "compute min of lat, in station;"
    COMPUTE_MAX_LAT = "compute max of lat, in station;"
    COMPUTE_MIN_LON = "compute min of lon, in station;"
    COMPUTE_MAX_LON = "compute max of lon, in station;"

    COMPUTE_CENTRALITY_TUNNEL_KCORE = "compute centrality of station, using k-core;"
    COMPUTE_CENTRALITY_ROUTE_KCORE = "compute centrality of station, in [station, route], using k-core;"
    ANALYTICAL_QUERIES = [COMPUTE_CENTRALITY_TUNNEL_KCORE,
        COMPUTE_CENTRALITY_ROUTE_KCORE]

    def __init__(self, session, root=tk.Tk()):
        """
            Main visualisation class. Builds an interactive map of the Paris tube.
            :param root:
            :param client:
        """

        start_time = datetime.datetime.now()

        self._root = root
        self._session = session
        self.w, self.h = self._root.winfo_screenwidth(), self._root.winfo_screenheight()
        self._root.geometry("%dx%d+0+0" % (self.w, self.h))
        self._root.focus_set()
        self._root.bind("<Escape>", lambda e: e.widget.quit())
        self._root.bind("<Key>", self._key_handler)
        self._root.title('Paris Tube Map')
        self._canvas = tk.Canvas(self._root)
        self._canvas.bind("<ButtonPress-1>", self._scan_start)
        self._canvas.bind("<ButtonRelease-1>", self._scan_stop)
        self._canvas.bind("<B1-Motion>", self._scan_move)
        # Stretch canvas to root window size.
        self._canvas.pack(fill=tk.BOTH, expand=1)

        # We want to scale the longitude and lonitude to fit the image
        # To do this we need the minimum and maximum of the longitude and latitude,
        # we can query for this easily in Grakn!
        with session.transaction().read() as transaction:
            self.min_lat = list(execute_and_log(
                self.COMPUTE_MIN_LAT, transaction))[0].number()
            print("Compute min of lat")
            print("Result :")
            print(self.min_lat)

            self.max_lat = list(execute_and_log(
                self.COMPUTE_MAX_LAT, transaction))[0].number()
            print("Compute max of lat")
            print("Result :")
            print(self.max_lat)

            self.min_lon = list(execute_and_log(
                self.COMPUTE_MIN_LON, transaction))[0].number()
            print("Compute min of lon")
            print("Result :")
            print(self.min_lon)

            self.max_lon = list(execute_and_log(
                self.COMPUTE_MAX_LON, transaction))[0].number()
            print("Compute max of lon")
            print("Result :")
            print(self.max_lon)

        # aspect ratio as width over height, which is longitude over latitude
        aspect_ratio = (self.max_lon - self.min_lon) / \
                        (self.max_lat - self.min_lat)
        self.new_width = self.w
        self.new_height = self.new_width / aspect_ratio

        # We need to associate the id of the station entity in Grakn to the rendered dot on the screen, so that we can
        # find the Grakn id of a station that is clicked on
        self._station_point_ids = dict()
        # Also store the station coords so that we don't have to query Grakn for them again
        self._station_canvas_coords = dict()
        self._station_centrality_points = dict()

        self._draw()

        # self._draw_stations()

        # ===== Event state variables =====
        self._displaying_centrality = False
        self._scale = 1
        self._shortest_path_stations = []
        self._shortest_path_elements = []
        self._scan_delta = (0, 0)
        self._x_pos = 0
        self._y_pos = 0
        self._scanning = False

        end_time = datetime.datetime.now()
        print("- - - - - -\nTime taken: " + str(end_time - start_time))

    @staticmethod
    def get_visualisation_data(session):

        """
        Retrieve the data required for visualising the tube network
        :return: coordinates of all stations and their names
        """

        with session.transaction().read() as transaction:
            print("\nRetriving coordinates to draw stations and tunnels ...")
            coordinates = {}
            id = 0

            #This request is used to get all pairs of stations that are connected by a route
            #We match all route in the db and get the line and the two connected stations
            answers_iterator = execute_and_log(
                ' match $route ($sta1, $sta2) isa route, has station_ligne $ligne; get $sta1, $sta2, $ligne ;', transaction
            )

            for answer in answers_iterator:
                tube_line_name = answer.get('ligne').value()
                station1 = answer.get('sta1').id
                station2 = answer.get('sta2').id

                #Now we match and get all the information from the two connected stations (thanks to their ids)
                origin_iterator = execute_and_log(
                    'match $station1 id ' + station1+', has name $origin ,has station_id $id_beginning, has lat $lat1, has lon $lon1; get $id_beginning,$origin, $lat1, $lon1;', transaction)
                end_iterator = execute_and_log(
                    'match $station2 id '+station2+', has name $destination, has station_id $id_end, has lat $lat2, has lon $lon2; get $id_end,$destination, $lat2, $lon2;', transaction)
                id = id + 1


                for origin1 in origin_iterator:
                    origin = origin1.get('origin').value()
                    lon1, lat1 = origin1.get(
                        'lon1').value(), origin1.get('lat1').value()
                    id_beginning = origin1.get("id_beginning").value()

                for end1 in end_iterator:
                    destination = end1.get('destination').value()
                    lon2, lat2 = end1.get(
                        'lon2').value(), end1.get('lat2').value()
                    id_end = end1.get("id_end").value()

                #And we append the results in the dict with all the others
                coordinates[id] = {
                    "station_ligne": [tube_line_name],
                    "from": {
                        "lon": lon1,
                        "lat": lat1,
                        "station_name": origin,
                        "station_id": id_beginning

                    },
                    "to": {
                        "lon": lon2,
                        "lat": lat2,
                        "station_name": destination,
                        "station_id": id_end
                    }
                }
        return coordinates

    @staticmethod
    def find_shortest_path(session, ids):

        with session.transaction().read() as transaction:

            query = 'compute path from ' + ids[0] + ', to ' + ids[1] + ';'
            try:
                shortest_path_concept_list = list(
                    execute_and_log(query, transaction))[0]

                # The response contains the different permutations for each path through stations. We are interested only in
                # which stations the path passes through
                shortest_path_ids = []
                for shortest_path_node_id in shortest_path_concept_list.list():
                    concepts_list = list(transaction.query(
                        "match $sta id " + shortest_path_node_id + "; $sta has name $nam; get;"))
                    if len(concepts_list) > 0:
                        concept = concepts_list[0]
                        if concept.map().get("sta").type().label() == 'station':
                            shortest_path_ids.append(shortest_path_node_id)
                return shortest_path_ids
            except:
                print("CHEMIN NON TROUVÉ / NON DISPONIBLE")

    @staticmethod
    def compute_centrality(session, query):
        centrality_details = {
            "centrality_set": [],
            "max_score": 0
        }

        with session.transaction().read() as transaction:
            centralities = list(execute_and_log(query, transaction))
            # Find the max centrality value, that way we can scale the visualisation up to a maximum radius
            centrality_details["max_score"] = max(
                [int(centrality.measurement()) for centrality in centralities])

            for centrality in centralities:
                centrality_set = {
                    "measurement": centrality.measurement(),
                    "concept_ids": []
                }

                for concept_id in centrality.set():
                    centrality_set["concept_ids"].append(concept_id)

                centrality_details["centrality_set"].append(centrality_set)

        print(centrality_details)

        return centrality_details


    def Draw_seine(self):

        # Grid coordinates of a path along the centre-line of La Seine in Paris
        SEINE_waypoint = ((48.772773, 2.411356),(48.776891, 2.414646),(48.780865, 2.417483),(48.789266, 2.422638),(48.796402, 2.420453),(48.803774, 2.411313),(48.810861, 2.409492),(48.817982, 2.405901),(48.822129, 2.395588),(48.827270, 2.387981),(48.833969, 2.379891),(48.839630, 2.373289),(48.841611, 2.370717),(48.844485, 2.366576),
            (48.846830, 2.363550),(48.850086, 2.357603),(48.852350, 2.352977),(48.854405, 2.347717),(48.856159, 2.343282),(48.858270, 2.3384868),(48.859230, 2.334001),(48.860105, 2.330278),
            (48.862279, 2.323819),(48.863648, 2.318809),(48.863739, 2.313971),(48.863626, 2.310742),(48.863668, 2.308489),(48.863569, 2.303575),(48.863421, 2.300507),(48.861685, 2.294263),
            (48.859483, 2.291173),(48.857351, 2.288748),(48.855614, 2.286731),(48.854124, 2.285014),(48.852540, 2.282690),(48.850782, 2.280297),(48.849389, 2.278434),(48.847447, 2.276385),
            (48.845534, 2.274261),(48.842688, 2.271418),(48.838428, 2.267431),(48.834586, 2.263558),(48.830250, 2.258462),(48.824797, 2.249568),(48.823117, 2.237919),(48.830194, 2.226450),
            (48.839076, 2.222887),(48.849427, 2.225365),(48.862338, 2.226384),(48.872883, 2.237832),(48.885122, 2.253422),(48.885122, 2.253422),(48.902401, 2.283997),(48.908843, 2.298647),(48.916216, 2.320786),(48.929868, 2.337285),(48.943158, 2.336514),(48.950066, 2.305815),(48.947636, 2.272512),)

        scaled_thames_coords = []
        for lat, lon in SEINE_waypoint:
            lon, lat = self._transform_coords(lon, lat)
            scaled_thames_coords.append((lon, lat))

        self._canvas.create_line(
            *scaled_thames_coords,
            width=self.SEINE_WIDTH,
            fill=self.SEINE_COLOR,
            joinstyle=tk.ROUND
        )

    def _transform_coords(self, lon, lat):

        """
        Transfrom grid coordinates to canvas coordinates
        :param lon: grid coordinate longitude
        :param lat: grid coordinate latitude
        :return: transformed coordination
        """

        return transform_coords(
            lon, lat, self.min_lon, self.max_lon, self.min_lat, self.max_lat, self.new_width, self.new_height
        )

    
    def _draw(self):

        """
        Draws everything in the visualiser
        """

        print("\nDrawing ...")
        self.Draw_seine()
        coordinates = self.get_visualisation_data(self._session)

        drawn_station_name = []
        
        for  tube_id,details in coordinates.items():

            TUBE_LINE_COLOURS = {
                "M1": "#FFCD00",
                "M2": "#003CA6",
                "M3": "#837902",
                "M4": "#CF009E",
                "M5": "#FF7E2E",
                "M6": "#6ECA97",
                "M7": "#FA9ABA",
                "M7 bis": "#6ECA97",
                "M7b": "#6ECA97",
                "M8": "#E19BDF",
                "M9": "#B6BD00",
                "M10": "#C9910D",
                "M11": "#704B1C",
                "M12": "#007852",
                "M13": "#6EC4E8",
                "M14": "#62259D",
                "3 bis": "#6EC4E8",
                "M3 bis": "#6EC4E8",
                "M3b": "#6EC4E8",
            }

            print("Drawing tunnels..")

            # Draw tunnels
            for i, tube_line_name in enumerate(details["station_ligne"]):

                print(i,tube_line_name)
                # Trigonometry to draw parallel lines with consistent distance between them
                from_lon, from_lat = self._transform_coords(float(details["from"]["lon"]), float(details["from"]["lat"]))
                to_lon, to_lat = self._transform_coords(float(details["to"]["lon"]), float(details["to"]["lat"]))

                x = to_lon - from_lon
                y = to_lat - from_lat
                coords_1 = (float(details["from"]["lat"]),float(details["from"]["lon"]))
                coords_2 = (float(details["to"]["lat"]),float(details["to"]["lon"]))
                z = self.LINE_SPACING  # desired orthogonal displacement of parallel lines
                    
                grad = y / x  # gradient of the connection to draw


                # The change in coordinates needed to achieve this
                y = ((grad ** 2 + 1) ** -0.5) * z
                x = grad * y

                self._canvas.create_line(
                    from_lon - (i * x),
                    from_lat + (i * y),
                    to_lon - (i * x),
                    to_lat + (i * y),
                    fill=TUBE_LINE_COLOURS[tube_line_name],
                    width=self.LINE_WIDTH
                )
            
            print("All tunnels drawn..")

            
            
            print("Drawing stations on the map..")
        

        # Draw stations
        # We request all the stations one by one and get their informations.

        with GraknClient(uri="localhost:48555") as client:
            with client.session(keyspace = "paris_subway") as session:
                with session.transaction().read() as transaction:
                    answer_iterator = execute_and_log('match $x isa station, has name $name,has lat $lat, has lon $lon ,has station_id $station_id;get $x, $lat,$lon, $name,$station_id;',transaction)

                    for i in answer_iterator :
                        station_id = i.get("station_id").value()
                        station_name = i.get("name").value()
                        ids = i.get("x")
                        ids = ids.id
                        if station_name not in drawn_station_name: # draw each station only once
                            lon, lat = self._transform_coords(float(i.get("lon").value()), float(i.get("lat").value()))

                            # Write label
                            station_label_tag = self._canvas.create_text(
                                lon + self.STATION_CIRCLE_RADIUS,
                                lat + self.STATION_CIRCLE_RADIUS,
                                text=station_name,
                                anchor=tk.NW,
                                font=('Johnston', self.STATION_FONT_SIZE, 'bold'),
                                fill="#666"
                            )

                            # Draw circle
                            station_tag = self._canvas.create_circle(
                                lon,
                                lat,
                                self.STATION_CIRCLE_RADIUS,
                                fill="white",
                                outline="black"
                            )

                            self._station_canvas_coords[station_name] = (lon, lat)
                            self._station_point_ids[ids] = station_tag

                            # station selection event handlers
                            def callback_wrapper(event, id=ids): return self._on_station_select(ids)
                            event_sequence = "<Shift-ButtonPress-1>"
                            self._canvas.tag_bind(station_tag, event_sequence, callback_wrapper)
                            self._canvas.tag_bind(station_label_tag, event_sequence, callback_wrapper)

                            drawn_station_name.append(station_name)
            
        print("All stations drawn..")
        print("\nDone! you can now interact with the visualiser.")


    def _scan_start(self, event):
        """
            Processes the start of dragging with the mouse to pan
            :param event: event instance
        """
        self._canvas.scan_mark(event.x, event.y)
        self._scan_start_pos = event.x, event.y
        self._scanning = True

    def _scan_move(self, event):
        """
            Processes moving the mouse during dragging to pan
            :param event: event instance
        """
        self._canvas.scan_dragto(event.x, event.y, gain=1)
        self._scan_delta = event.x - self._scan_start_pos[0], event.y - self._scan_start_pos[1]

    def _scan_stop(self, event):
        """
            Processes the end of dragging with the mouse to pan
            :param event: event instance
        """
        self._x_pos += self._scan_delta[0]
        self._y_pos += self._scan_delta[1]
        self._scan_delta = (0, 0)
        self._scanning = False

    def _key_handler(self, event):
        """
            Handle a key press event, dispatching to the desired behaviour
            :param event: event instance, including the character that was pressed
        """
        if event.char == "+" or event.char == "=":
            self.zoom("in")

        if event.char == "-" or event.char == "_":
            self.zoom("out")

        if not self._displaying_centrality:


            if event.char == self.STATION_K_CORE_KEY:
                self.display_centrality(self.COMPUTE_CENTRALITY_TUNNEL_KCORE, self.STATION_K_CORE_MAX_RADIUS, self.STATION_K_CORE_COLOUR)
            if event.char == self.STATION_ROUTE_KEY:
                self.display_centrality(self.COMPUTE_CENTRALITY_ROUTE_KCORE, self.STATION_DEGREE_MAX_RADIUS, self.STATION_DEGREE_COLOUR)

        if event.char == self.CLEAR_SHORTEST_PATH_KEY:
                self.clear_shortest_path()

        if event.char == self.CLEAR_ALL_KEY:
            self.clear_all()

    def _on_station_select(self, station_id):
        
        """
        To be called when the user selects a station. Needs to be passed the unique Naptan-id of the station
        :param event:
        :param station_id:
        :return:
        """

        self._shortest_path_stations.append(station_id)

        x, y = self._get_station_point_coords(station_id)
        r = self._transform_to_current_scale(2 * self.STATION_CIRCLE_RADIUS)
        c = self._canvas.create_circle(x, y, r, fill=self.TUNNEL_SHORTEST_PATH_COLOUR, outline="")
        self._canvas.tag_lower(c, 1)

        self._shortest_path_elements.append(c)
        print("IDs station départ -> station arrivée")
        print(self._shortest_path_stations)
        print("Veuillez patienter pendant que je recherche un itinéraire..")

        if len(self._shortest_path_stations) > 1:
            shortest_path_ids = self.find_shortest_path(self._session, [self._shortest_path_stations[-2], self._shortest_path_stations[-1]])
            print(" ")
            print("********************RESULTS******************************")
            print(" ")
            print("IDs of the passage station : " )
            print(shortest_path_ids)
            print("--------------------------------------")
            for station_id in shortest_path_ids:
                with GraknClient(uri="localhost:48555") as client:
                    with client.session(keyspace = "paris_subway") as session:
                        with session.transaction().read() as transaction:

                            # Add a point on the path for every station on the path
                            answers_iterator = execute_and_log('match $station id '+station_id+',has station_ligne $station_ligne,has name $station_name,has station_id $station_id, has lat $lat, has lon $lon;get $station_id, $lat, $lon,$station_name,$station_ligne;' ,transaction)
                            for i in answers_iterator :
                                name = i.get('station_name').value()
                                station_ligne = i.get('station_ligne').value()
                                print("    |")
                                print("    |")
                                print(" ")
                                sys.stdout.write(name)
                                sys.stdout.write(" ")
                                sys.stdout.write(station_ligne)
                                print(" ")
                                

            self.display_shortest_path(shortest_path_ids)

    def display_shortest_path(self, shortest_path_ids):
        """
        Renders the shortest path(s) from station to station
        :param shortest_path_ids: response from Grakn server
        """

        path_points = []
        coord_liste = []
        for station_id in shortest_path_ids:
            with GraknClient(uri="localhost:48555") as client:
                with client.session(keyspace = "paris_subway") as session:
                    with session.transaction().read() as transaction:
                        # Add a point on the path for every station on the path
                        answers_iterator = execute_and_log('match $station id '+station_id+',has name $station_name,has station_id $station_id, has lat $lat, has lon $lon;get $station_id, $lat, $lon,$station_name;' ,transaction)
                        for i in answers_iterator :
                            # id_d = i.get('station_id').value()
                            lat = i.get('lat').value()
                            lon = i.get('lon').value()
                            name = i.get('station_name').value()
                            print(name)
                            coord_liste.append(lon)
                            coord_liste.append(lat)
                            
        j = 0
        while(j < len(coord_liste)-3) :

            lon1, lat1 = self._transform_coords(coord_liste[j], coord_liste[j+2])
            lon2, lat2 = self._transform_coords(coord_liste[j+1], coord_liste[j+3])
            
            x = lon2 - lon1
            y = lat2 - lat1
            grad = y / x  # gradient of the connection to draw
            # The change in coordinates needed to achieve this
            z = self.LINE_SPACING
            y = ((grad ** 2 + 1) ** -0.5) * z
            x = grad * y
            self._canvas.create_line(
                lon1,
                lat1,
                lon2,
                lat2,
                fill="#E22901",width=self.LINE_WIDTH)
            j += 2
            print("Route drawn..")



        path = self._canvas.create_line(path_points, width=self.TUNNEL_SHORTEST_PATH_WIDTH, fill=self.TUNNEL_SHORTEST_PATH_COLOUR, joinstyle=tk.ROUND, dash=(3, 3))
        self._shortest_path_elements.append(path)


        # Put the path behind the other visual elements on the map
        self._canvas.tag_lower(path, 1)

    def _get_station_point_coords(self, station_id):
        """
        Get the canvas coordinates of a station from its ID
        :param station_id: the ID of the desired station
        :return: the centre-point coordinates of the circle used to represent the station
        """
        x0, y0, x1, y1 = self._canvas.coords(self._station_point_ids[station_id])
        point = (x0 + x1) / 2, (y0 + y1) / 2
        return point

    def clear_shortest_path(self):
        """
        Delete from the canvas the elements being used to display shortest paths
        """
        self._canvas.delete(*self._shortest_path_elements)
        self._shortest_path_stations = []

    def clear_all(self):
        self.clear_shortest_path()
        self.hide_centrality()

    def zoom(self, direction):
        """
        "Zoom" the screen to magnify details. This entails scaling up the whole canvas, and some slightly complex
        translation of the canvas to give the effect of zooming in on the canvas point that sits at the centre of
        the window
        :param direction: "in" or "out", whether to magnify or de-magnify the map
        """
        if self._scanning:
            print("Currently scanning. Stop scanning to zoom.")
        else:
            if direction == "in":
                scaling = self.ZOOM_IN_SCALE
            elif direction == "out":
                scaling = self.ZOOM_OUT_SCALE
            else:
                raise ValueError("Call to zoom didn't specify a valid direction")

            # First, scale up the canvas about its origin. Doing this about the canvas origin keeps adding other
            # elements to the canvas simple, because then only scaling needs to be applied
            self._canvas.scale('all', 0, 0, scaling, scaling)

            # Update the persistent scale value
            self._scale *= scaling

            # Find the displacement to shift the canvas by, so that is appears to scale about the centre-point of the
            # window
            dx = -int((1 - scaling) * (self._x_pos - self.w / 2))
            dy = -int((1 - scaling) * (self._y_pos - self.h / 2))

            # Since we're shifting by this amount, also add this displacement to the persistent scan variables
            self._x_pos += dx
            self._y_pos += dy

            # Set an anchor to drag from. I believe this point is arbitrary
            self._canvas.scan_mark(0, 0)

            # The canvas is being scaled about its origin, so we only need to drag the delta to centre the scaling
            self._canvas.scan_dragto(dx, dy, gain=1)

    def _transform_to_current_scale(self, val):
        """
        Take a value, e.g. a coordinate, and scale it according to the current scaling of the canvas. This is mostly
        for the benefot of adding or removing rendered elements after the map has been zoomed
        :param val:
        :return:
        """
        return val * self._scale

    def display_centrality(self, query, upper_radius, colour):
        """
            Show an infographic-style visualisation of centrality, where the radius of the circles plotted corresponds to
            the centrality score
            :param query: graql centrality query as a string
            :param upper_radius:
            :param colour:
            :return:
        """
        with GraknClient(uri="localhost:48555") as client:
            with client.session(keyspace = "paris_subway") as session:
                with session.transaction().read() as transaction:

                    centrality_details = self.compute_centrality(self._session, query)

                    for centrality_set in centrality_details["centrality_set"]:
                        radius = self._transform_to_current_scale(
                            (int(int(centrality_set["measurement"])) / centrality_details["max_score"]) * upper_radius
                        )

                         

                        for concept_id in centrality_set["concept_ids"]:
                            print(concept_id, centrality_set["measurement"], centrality_details["max_score"])

                            answers_iterator = execute_and_log(' match $x id '+concept_id+', has station_id $station_id, has name $station_name; get $station_id, $station_name;',transaction)
                            for i in answers_iterator :
                                id_d = i.get('station_id').value()
                                station_name = i.get('station_name').value()
                            station_element_id = id_d
                            print(station_name)
                            print(id_d)

                            lon, lat = self._station_canvas_coords[station_name]
                            lon = self._transform_to_current_scale(lon)
                            lat = self._transform_to_current_scale(lat)

                            centrality_element_id = self._canvas.create_circle(lon, lat, radius, fill=colour, outline="")

                            self._station_centrality_points[concept_id] = centrality_element_id

                            # Send the drawn elements to behind the station point
                            self._canvas.tag_lower(centrality_element_id, station_element_id)
                    print(self._station_centrality_points)
                    self._displaying_centrality = True

    def hide_centrality(self):
        if self._displaying_centrality:
            for concept_id, point_id in self._station_centrality_points.items():
                self._canvas.delete(point_id)
            self._displaying_centrality = False


def init(shouldHalt):
    root = tk.Tk() # Build the Tkinter application
    with GraknClient(uri="localhost:48555") as client:
        with client.session(keyspace="paris_subway") as session:
            tube_gui = TubeGui(session, root)
            if shouldHalt:
                root.mainloop()


if __name__ == "__main__":
    init(True)
