import json
from .utils import m_to_hm
from minizinc import Instance, Result
from collections import defaultdict

def parseResult(
    result: Result, instance: Instance, outputfile: str
) -> None:
    if not result:
        output = generateNoSolutionOutput(instance)
        save_json(output, outputfile)
        return

    output = generateVehicleTripsDict(instance, result)
    #save_json(output, outputfile.split(".")[0] + "_minizinc.json")
    
    # add connections between trips
    for v in output["vehicles"]:
        v["trips"] = findIntersections(v["trips"], instance["dist_matrix"])

    # add start/end depot trips
    for v in output["vehicles"]:
        first, last = get_first_and_last_trip(v, instance)
        v["trips"] = [first] + v["trips"] + [last]
    
    # merge vehicles
    output = merge_vehicles_by_id(output)
    #save_json(output, outputfile.split(".")[0] + "_test.json")

    # clean (only keep required fields)
    output_clean = clean_output(output, result)
    save_json(output_clean, outputfile)

def generateNoSolutionOutput(instance: Instance):
    output = { "requests": 0, "vehicles": [] }
    for v in instance["ids_v"]:
        output["vehicles"] += [{
            "id": v,
            "trips": [],
        }]

    return output

def generateVehicleTripsDict(instance: Instance, result: Result):
    p_min = min(instance["rids_a"])
    trips = defaultdict(list)
    for v, o, d, s, a, p in zip(
        result["v_a"],
        instance["org_a"],
        instance["dst_a"],
        result["s_a"],
        result["e_a"],
        instance["rids_a"],
    ):
        trips[v] += [
            {
                "origin": o,
                "destination": d,
                "start": s,
                "arrival": a,
                "patients": p,
                "srv": instance["srv_r"][p - p_min],
                "type": "original",
            }
        ]
        
    output = {}
    output["vehicles"] = []
    for v, t in trips.items():
        output["vehicles"] += [
            {
                "id": instance["ids_v"][v],
                "savail": [m_to_hm(instance["savail_v"][v])],
                "eavail": [m_to_hm(instance["eavail_v"][v])],
                "s_depot": instance["sd_v"][v],
                "e_depot": instance["ed_v"][v],
                "trips": sorted(t, key=lambda d: d["start"]),
            }
        ]

    return output

def getAllLocations(trips):
    locations = []
    
    for trip in trips:
        locations += [
            {
                "location": trip["origin"],
                "time": trip["start"],
                "patients": trip["patients"],
                "type": "embark",
                "srv": trip["srv"]
            },
            
            {
                "location": trip["destination"],
                "time": trip["arrival"],
                "patients": trip["patients"],
                "type": "disembark",
                "srv": trip["srv"]                
            }
        ]
    
    locations = sorted(locations, key=lambda d: d["time"])
    
    return locations
    
def findIntersections(trips, dist_matrix):    
    intersections = []
    passengers_stack = {}
    
    allLocations = getAllLocations(trips)
    for i in range(len(allLocations)):
        if(i != len(allLocations)-1):    
            
            if(allLocations[i]["type"] == "embark"):
                passengers_stack[allLocations[i]["patients"]] = True
            else:
                passengers_stack[allLocations[i]["patients"]] = False
            
            patients = []
            for key, value in passengers_stack.items():
                if(value):
                    patients.append(int(key))
            
            if(len(patients) != 0):
                if (allLocations[i]["type"] == "embark"):
                    intersections += [
                        {
                            "origin": allLocations[i]["location"],
                            "origin_type": allLocations[i]["type"],
                            "origin_patient": passengers_stack[allLocations[i]["patients"]],
                            "destination": allLocations[i+1]["location"],
                            "destination_type": allLocations[i+1]["type"],
                            "start": allLocations[i]["time"],
                            "arrival": allLocations[i]["time"] + dist_matrix[allLocations[i]["location"]][allLocations[i+1]["location"]] + allLocations[i]["srv"],
                            "patients": patients,
                            "srv": allLocations[i]["srv"],
                        }
                    ]
                else:
                    intersections += [
                        {
                            "origin": allLocations[i]["location"],
                            "origin_type": allLocations[i]["type"],
                            "origin_patient": passengers_stack[allLocations[i]["patients"]],
                            "destination": allLocations[i+1]["location"],
                            "destination_type": allLocations[i+1]["type"],
                            "start": allLocations[i]["time"],
                            "arrival": allLocations[i]["time"] + dist_matrix[allLocations[i]["location"]][allLocations[i+1]["location"]],
                            "patients": patients,
                            "srv": 0,
                        }
                    ]                    
            else:
                intersections += [
                    {
                        "origin": allLocations[i]["location"],
                        "origin_type": allLocations[i]["type"],
                        "origin_patient": passengers_stack[allLocations[i]["patients"]],
                        "destination": allLocations[i+1]["location"],
                        "destination_type": allLocations[i+1]["type"],
                        "start": allLocations[i]["time"],
                        "arrival": allLocations[i]["time"] + dist_matrix[allLocations[i]["location"]][allLocations[i+1]["location"]],
                        "patients": patients,
                        "srv": 0,
                    }
                ]                
    
    intersections_output = []     
    for i in range(len(intersections)):     
        if intersections[i]["origin"] != intersections[i]["destination"]:
            intersections_output.append(intersections[i])
               
    return intersections_output

def get_first_and_last_trip(v, instance: Instance):
    trips = v["trips"]

    # first
    first_trip = trips[0]
    o = v["s_depot"]
    d = first_trip["origin"]
    if o != d:
        new_first = {
                    "origin": o,
                    "destination": d,
                    "start": first_trip["start"] - instance["dist_matrix"][o][d],
                    "arrival": first_trip["start"],
                    "patients": [],
                    "type": "START"
        }

    # last
    last_trip = trips[-1]
    d = v["e_depot"]
    o = last_trip["destination"]
    if o != d:
        new_last = {
                    "origin": o,
                    "destination": d,
                    "start": last_trip["arrival"] + last_trip["srv"],
                    "arrival": last_trip["arrival"] + last_trip["srv"] + instance["dist_matrix"][o][d],
                    "patients": [],
                    "type": "END"
        }
    
    return new_first, new_last
        
def merge_vehicles_by_id(output):
    # merge vehicles by id
    v_id2i = defaultdict(list)
    for i, v in enumerate(output["vehicles"]):
        v_id2i[v["id"]] += [i]

    # merge
    for id, idx in v_id2i.items():
        if len(idx) > 1:
            merged = []
            for i in idx:
                merged += output["vehicles"][i]["trips"]

            output["vehicles"] += [{
                "id": id,
                "merged": True,
                "trips": sorted(merged, key=lambda d: d["arrival"])
            }]

    # delete unmerged
    counter = 0
    for id, idx in v_id2i.items():
        if len(idx) > 1:
            for i in idx:
                del output["vehicles"][i-counter]
                counter+=1
    
    return output


def clean_output(output, result):
    clean_vehicles = []
    for v in output["vehicles"]:
        trips = []
            
        for t in v["trips"]:
            t["start"] = m_to_hm(t["start"])
            t["arrival"] = m_to_hm(t["arrival"])            
            
            trips += [{
                "origin": t["origin"],
                "destination": t["destination"],
                "arrival": t["arrival"],
                "patients": t["patients"]
            }]
        clean_vehicles += [{ "id": v["id"], "trips": trips }]
    clean_output = {"requests": result["objective"],
                    "vehicles": sorted(clean_vehicles, key=lambda d: d["id"])}

    return clean_output

def save_json(dict, filename):
    with open(filename, "w") as outfile:
        json.dump(dict, indent=2, fp=outfile)
