import json

from .utils import hm_to_m
from typing import List, Tuple
from minizinc import Instance

def parseInput(json: json.__dict__, instance: Instance) -> None:
    parseAndSetRequests(json, instance)
    parseAndSetVehicles(json, instance)
    parseAndSetPlaces(json, instance)
    instance["dist_matrix"] = json["distMatrix"]
    instance["max_wait_time"] = hm_to_m(json["maxWaitTime"])

def parseAndSetPlaces(json: json.__dict__, instance: Instance) -> None:
    places = json["places"]

    instance["n_p"] = len(places)

def parseAndSetRequests(json: json.__dict__, instance: Instance) -> None:
    requests = json["patients"]

    # set variables inside mzn model
    instance["n_r"] = len(requests)
    instance["ids_r"] = [r["id"] for r in requests]
    instance["org_r"] = [r["start"] for r in requests]
    instance["dst_r"] = [r["destination"] for r in requests]
    instance["ret_r"] = [r["end"] for r in requests]

    instance["l_r"] = [r["load"] for r in requests]
    instance["c_r"] = [r["category"] for r in requests]
    instance["srv_r"] = [hm_to_m(r["srvDuration"]) for r in requests]
    instance["rdv_r"] = [hm_to_m(r["rdvTime"]) for r in requests]
    instance["drdv_r"] = [hm_to_m(r["rdvDuration"]) for r in requests]

    activities = []

    id_a = 0
    for r in requests:
        if r["end"] == -1:
            newActivity = {}
            newActivity["id"] = id_a
            newActivity["rid"] = r["id"]
            newActivity["reverse_activity_id"] = id_a
            newActivity["direction"] = 1
            newActivity["o"] = r["start"]
            newActivity["d"] = r["destination"]
            newActivity["l"] = r["load"]

            activities.append(newActivity)
            id_a += 1
        elif r["start"] == -1:
            newActivity = {}
            newActivity["id"] = id_a
            newActivity["rid"] = r["id"]
            newActivity["reverse_activity_id"] = id_a
            newActivity["direction"] = -1
            newActivity["o"] = r["destination"]
            newActivity["d"] = r["end"]
            newActivity["l"] = r["load"]

            activities.append(newActivity)
            id_a += 1
        else:
            newActivity = {}
            newActivity["id"] = id_a
            newActivity["rid"] = r["id"]
            newActivity["direction"] = 1

            id_a += 1

            newActivity2 = {}
            newActivity2["id"] = id_a
            newActivity2["rid"] = r["id"]
            newActivity2["direction"] = -1

            id_a += 1

            newActivity["reverse_activity_id"] = newActivity2["id"]
            newActivity["o"] = r["start"]
            newActivity["d"] = r["destination"]
            newActivity["l"] = r["load"]

            newActivity2["reverse_activity_id"] = newActivity["id"]
            newActivity2["o"] = r["destination"]
            newActivity2["d"] = r["end"]
            newActivity2["l"] = r["load"]

            activities.append(newActivity)
            activities.append(newActivity2)

    instance["n_a"] = len(activities)
    instance["ids_a"] = [a["id"] for a in activities]
    instance["rids_a"] = [a["rid"] for a in activities]
    instance["raids_a"] = [a["reverse_activity_id"] for a in activities]
    instance["dir_a"] = [a["direction"] for a in activities]
    instance["org_a"] = [a["o"] for a in activities]
    instance["dst_a"] = [a["d"] for a in activities]
    instance["l_a"] = [a["l"] for a in activities]


def parseAndSetVehicles(json: json.__dict__, instance: Instance) -> None:
    def setMinizincVehicleFleet(vehicleFleet: List[object]) -> List[object]:
        minizincVehicleFleet = []
        for vehicle in vehicleFleet:
            for availability in vehicle["availability"]:
                newVehicle = {}
                newVehicle["id"] = vehicle["id"]
                newVehicle["canTake"] = vehicle["canTake"]
                newVehicle["start"] = vehicle["start"]
                newVehicle["end"] = vehicle["end"]
                newVehicle["capacity"] = vehicle["capacity"]
                newVehicle["availability"] = availability

                minizincVehicleFleet.append(newVehicle)

        return minizincVehicleFleet

    # helper functions
    def setVehicleCategories(categories: List[int]) -> List[bool]:
        categoriesBool = [False, False, False]

        for category in categories:
            categoriesBool[category] = True

        return categoriesBool

    def setVehicleAvailabilities(availability: str) -> Tuple[int, int]:
        sAvails = []
        eAvails = []

        a = availability.split(":")

        return [hm_to_m(a[0]), hm_to_m(a[1])]

    # actual parsing starts here
    vehicleFleet = json["vehicles"]
    minizincVehicleFleet = setMinizincVehicleFleet(vehicleFleet)

    # set variables inside mzn model
    instance["svb"] = json["sameVehicleBackward"]

    instance["n_v"] = len(minizincVehicleFleet)
    instance["ids_v"] = [v["id"] for v in minizincVehicleFleet]

    instance["k_v"] = [v["capacity"] for v in minizincVehicleFleet]
    instance["C_v"] = [setVehicleCategories(v["canTake"]) for v in minizincVehicleFleet]

    instance["sd_v"] = [v["start"] for v in minizincVehicleFleet]
    instance["ed_v"] = [v["end"] for v in minizincVehicleFleet]

    savail_v = []
    eavail_v = []
    for vehicle in minizincVehicleFleet:
        availabilities = setVehicleAvailabilities(vehicle["availability"])
        savail_v += [availabilities[0]]
        eavail_v += [availabilities[1]]

    instance["savail_v"] = savail_v
    instance["eavail_v"] = eavail_v