#!/usr/bin/env -S pipenv run python

import json
import sys
import time

from src import parseInput, parseResult
from minizinc import Instance, Model, Solver

def main() -> None:
    
    if(len(sys.argv) < 3):
        print("Input Error: " + "Must use 2 args <input-file-name> <output-file-name")
        exit(1)

    inputFileName = sys.argv[1]
    outputFileName = sys.argv[2]

    ptp = Model("./ptp.mzn")
    solver = Solver.lookup("gecode")
    instance = Instance(solver, ptp)

    with open(inputFileName) as file:
        jsonInstance = json.load(file)
        parseInput(jsonInstance, instance)
    
    result = instance.solve()

    parseResult(result, instance, outputFileName)
    
if __name__ == "__main__":
    main()
