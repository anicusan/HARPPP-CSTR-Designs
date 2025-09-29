#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File   : async_access_template.py
# License: GNU v3.0


'''Run a user-defined simulation script with a given set of free parameter
values, then save the `error` value to disk.

ACCES takes an arbitrary simulation script that defines its set of free
parameters between two `# ACCESS PARAMETERS START / END` directives and
substitutes them with an ACCESS-predicted solution. After the simulation, it
saves the `error` variable to disk.

This simulation setup is achieved via a form of metaprogramming: the user's
code is modified to change the `parameters` to what is predicted at each run,
then code is injected to save the `error` variable. This generated script is
called in a massively parallel environment with two command-line arguments:

    1. The path to this run's `parameters`, as predicted by ACCESS.
    2. A path to save the user-defined `error` variable to.

You can find them in the `access_seed<seed>/results` directory.
'''


import os
import sys
import pickle


###############################################################################
# ACCESS INJECT USER CODE START ###############################################
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File   : simulation_script.py
# License: GNU v3.0
# Author : Andrei Leonard Nicusan <leonard@evophase.co.uk>
# Date   : 08.09.2024


import os
import sys
import shutil
import subprocess
from glob import glob

import rtoml
import numpy as np
from natsort import natsorted

# ACCESS PARAMETERS START

# Unpickle `parameters` from this script's first command-line argument and set
# `access_id` to a unique simulation ID

import coexist

def create_parameters(**kw):
    variables = list(kw.keys())
    minimums = [kw[v][0] for v in variables]
    maximums = [kw[v][1] for v in variables]
    values = [(kw[v][2] if (len(kw[v]) == 3) else ((kw[v][0] + kw[v][1]) / 2)) for v in variables]
    return coexist.create_parameters(variables, minimums, maximums, values)
with open(sys.argv[1], 'rb') as f:
    parameters = pickle.load(f)
access_id = 'JM-BaseCase'

access_id = int(sys.argv[1].split(".")[-2])
# ACCESS PARAMETERS END


# Create trial directory
assert os.path.isdir("Simulations")
trial_path = f"Simulations/sim{access_id:0>4}"
if not os.path.isdir(trial_path):
    os.mkdir(trial_path)


def system(cmd, cwd=None):
    if cwd is None:
        print("Running command:", cmd, flush=True)
    else:
        print("Running command:", cmd, "in", cwd, flush=True)
    subprocess.run(cmd, check=True, cwd=cwd)


def system_timeout(cmd, timeout, cwd=None):
    print(f"Running command with timeout {timeout / 3600} h:", cmd, flush=True)

    # Launch the process and wait
    process = subprocess.Popen(cmd, cwd=cwd)
    try:
        process.wait(timeout=timeout)

        # If simulation crashed, propagate the error and stop code
        if process.returncode != 0:
            os._exit(1)                     # Kills thread without raising an exception

    except subprocess.TimeoutExpired:
        print("Process exceeded the timeout. Terminating...")
        process.terminate()                 # Try to terminate the process gracefully
        try:
            process.wait(timeout=10)        # Wait a bit for it to terminate
        except subprocess.TimeoutExpired:
            print("Process did not terminate, killing it...")
            process.kill()                  # Force kill if it did not terminate
        return False
    return True


def create_case(parameters, trial_path):

    # Copy template into trial directory
    shutil.copytree("Template", trial_path, dirs_exist_ok=True)

    # Compute vessel sizes, placements, impeller sizes, placements
    vessel_height = 2000
    vessel_base_clearance = 600
    vessel_diameter = 2000

    bottom_clearance = float(parameters["value"]["bottom_clearance"])
    vessel_height0 = vessel_base_clearance - vessel_height * bottom_clearance

    xplace = float(parameters["value"]["xplace"])
    vessel_xtranslate = -vessel_diameter / 2 * xplace

    yplace = float(parameters["value"]["yplace"])
    vessel_ytranslate = -vessel_diameter / 2 * yplace

    impeller_height_ratio = float(parameters["value"]["impeller/height_ratio"])
    impeller_height = vessel_height * (1 - bottom_clearance) * impeller_height_ratio

    max_translate = max(abs(xplace), abs(yplace))
    impeller_diameter_ratio = float(parameters["value"]["impeller/diameter_ratio"])
    impeller_diameter = vessel_diameter * (1 - max_translate) * impeller_diameter_ratio

    # Update vessel settings to optimise
    with open(f"{trial_path}/phase-1-geometry-vessel/settings.toml") as f:
        settings = rtoml.load(f)

    settings["height0"] = vessel_height0
    settings["xtranslate"] = vessel_xtranslate
    settings["ytranslate"] = vessel_ytranslate

    with open(f"{trial_path}/phase-1-geometry-vessel/settings.toml", "w") as f:
        rtoml.dump(settings, f)

    # Update impeller settings to optimise
    with open(f"{trial_path}/phase-2-geometry-impeller/settings.toml") as f:
        settings = rtoml.load(f)

    settings["height"] = impeller_height
    settings["diameter"] = impeller_diameter

    settings["Blades"][0]["place_rel"] = float(parameters["value"]["impeller/0/place_rel"])
    settings["Blades"][0]["xlen_rel"] = float(parameters["value"]["impeller/0/xlen_rel"])
    settings["Blades"][0]["ylen_rel"] = float(parameters["value"]["impeller/0/ylen_rel"])

    settings["Blades"][0]["joint_place"] = float(parameters["value"]["impeller/0/joint_place"])
    settings["Blades"][0]["joint_angle"] = float(parameters["value"]["impeller/0/joint_angle"])

    settings["Blades"][0]["lean_place"] = float(parameters["value"]["impeller/0/lean_place"])
    settings["Blades"][0]["lean_angle"] = float(parameters["value"]["impeller/0/lean_angle"])

    settings["Blades"][0]["turn_place"] = float(parameters["value"]["impeller/0/turn_place"])
    settings["Blades"][0]["turn_angle"] = float(parameters["value"]["impeller/0/turn_angle"])

    settings["Blades"][0]["twist"] = float(parameters["value"]["impeller/0/twist"])
    settings["Blades"][0]["helix"] = float(parameters["value"]["impeller/0/helix"])
    settings["Blades"][0]["curl"] = float(parameters["value"]["impeller/0/curl"])

    settings["Blades"][0]["around_number"] = round(parameters["value"]["impeller/0/around_number"])
    settings["Blades"][0]["repeat_number"] = round(parameters["value"]["impeller/0/repeat_number"])
    settings["Blades"][0]["repeat_heights_equal"] = float(parameters["value"]["impeller/0/repeat_heights_equal"])
    settings["Blades"][0]["repeat_angles_bias"] = float(parameters["value"]["impeller/0/repeat_angles_bias"])

    settings["FidgetSurface"][0]["alpha1"] = float(parameters["value"]["impeller/fidgetsurface/0/alpha1"])
    settings["FidgetSurface"][0]["beta1"] = float(parameters["value"]["impeller/fidgetsurface/0/beta1"])

    with open(f"{trial_path}/phase-2-geometry-impeller/settings.toml", "w") as f:
        rtoml.dump(settings, f)

    # Update meshing settings based on impeller settings
    with open(f"{trial_path}/phase-4-mesh/settings.toml") as f:
        settings = rtoml.load(f)

    # Allow 50 mm around the impeller for rotation cylinder
    rotation_height0 = -50e-3
    rotation_height1 = impeller_height / 1000 + 50e-3
    rotation_radius = impeller_diameter / 1000 / 2 + 50e-3

    settings["RotationVolume"]["height0"] = rotation_height0
    settings["RotationVolume"]["height1"] = rotation_height1
    settings["RotationVolume"]["radius"] = rotation_radius

    # Keep the same mesh size as for the JM case, where for a rotation radius of 0.5, we had xscale = 0.5
    settings["Mesh"]["xscale"] = 0.5 * 0.5 / rotation_radius
    settings["Mesh"]["yscale"] = 0.5 * 0.5 / rotation_radius
    settings["Mesh"]["zscale"] = 0.5 * 0.5 / rotation_radius

    with open(f"{trial_path}/phase-4-mesh/settings.toml", "w") as f:
        rtoml.dump(settings, f)


def mesh_case(case_path):
    # Create CAD geometry
    system([sys.executable, "script.py"], cwd=f"{case_path}/phase-1-geometry-vessel")
    system([sys.executable, "script.py"], cwd=f"{case_path}/phase-2-geometry-impeller")

    # Mesh; sometimes SHM hangs, so we use a timeout
    timeout = 50 * 60
    finished = system_timeout([sys.executable, "script.py"], timeout, cwd=f"{case_path}/phase-4-mesh")
    if not finished:
        raise RuntimeError("Meshing timed out")

    # Remove phase 2 decomposed mesh, as only the reconstructed one will be used
    system(["rm", "-rf"] + glob(f"{case_path}/phase-2-mesh/case/processor*"))


def run_case(case_path):
    # Stop CFD after 11 hours if it did not finish...
    timeout = 11 * 60 * 60
    system_timeout([sys.executable, "script.py"], timeout, cwd=f"{case_path}/phase-5-cfd")

    # Remove phase 4 and 5 reconstructed meshes, as they are available decomposed in phase 5
    system(["rm", "-rf", "constant/polyMesh"], cwd=f"{case_path}/phase-4-mesh/case")
    system(["rm", "-rf", "constant/polyMesh"], cwd=f"{case_path}/phase-5-cfd/case")


create_case(parameters, trial_path)
mesh_case(trial_path)
run_case(trial_path)


# Extract results from last second
cov_dirs = natsorted(os.listdir(f"{trial_path}/phase-5-cfd/case/postProcessing/volFieldValue1.CoV/"))
latest_cov_path = f"{trial_path}/phase-5-cfd/case/postProcessing/volFieldValue1.CoV/{cov_dirs[-1]}/volFieldValue.dat"
cov_data = np.loadtxt(latest_cov_path, skiprows=4)
time_selection = cov_data[:, 0] > cov_data[-1, 0] - 1
epsilon_cov = cov_data[time_selection, 1].mean()

avg_dirs = natsorted(os.listdir(f"{trial_path}/phase-5-cfd/case/postProcessing/volFieldValue1.volAverage/"))
latest_avg_path = f"{trial_path}/phase-5-cfd/case/postProcessing/volFieldValue1.volAverage/{avg_dirs[-1]}/volFieldValue.dat"
avg_data = np.loadtxt(latest_avg_path, skiprows=4)
time_selection = avg_data[:, 0] > avg_data[-1, 0] - 1
epsilon_avg = avg_data[time_selection, 1].mean()


# Print results
print("Epsilon average:", epsilon_avg)
print("Epsilon CoV:", epsilon_cov)


# Only consider cases that ran for at least 20 seconds
final_time = avg_data[-1, 0]
if final_time < 20:
        raise RuntimeError("Simulation did not run for 20 seconds")


# Cap epsilon CoV at 0.5; below this value, it is not important
epsilon_cov = max(epsilon_cov, 0.5)


# Maximise epsilon average and minimise epsilon CoV
error = [-epsilon_avg, 1 / epsilon_cov]
# ACCESS INJECT USER CODE END   ###############################################
###############################################################################


# Save the user-defined `error` and `extra` variables to disk.
with open(sys.argv[2], "wb") as f:
    pickle.dump(error, f)

if "extra" in locals() or "extra" in globals():
    path = os.path.split(sys.argv[2])
    path = os.path.join(path[0], path[1].replace("result", "extra"))
    with open(path, "wb") as f:
        pickle.dump(extra, f)
