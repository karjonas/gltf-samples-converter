#!/usr/bin/env python
import subprocess
import os
from shutil import copy2, copytree
from argparse import ArgumentParser
import xml.etree.cElementTree as ET
import json
from multiprocessing import Pool
import re

#./generate-quick3d-project.py -o Q:\Code\temp -b Q:\Code\qt5-5.15-msvc2019\qtbase\bin\balsam.exe -i 2.0

def copy_template_files(output_dir):
    copy2("templates/main.cpp", output_dir)
    copy2("templates/main.qml", output_dir)
    copy2("templates/lightBaking.pro", output_dir)
    copy2("templates/lightBaking.qrc", output_dir)
    copy2("templates/config.json", output_dir)

def generate_qrc_files(output_dir):
    original_dir = os.getcwd()
    os.chdir(output_dir)

    qrcList = ["lightBaking.qrc"]
    # for each folder, generate a qrc file for all the files in the subtree
    for model in sorted(os.listdir(".")):
        # models will only be in folders
        if not os.path.isdir(model):
            continue

        os.chdir(model)
        qrcRoot = ET.Element("RCC")
        qrcResource = ET.SubElement(qrcRoot, "qresource", prefix="/" + model)

        componentName = ""
        for resource in sorted(os.listdir(".")):
            if not os.path.isdir(resource):
                if resource.endswith(".qrc"):
                    continue
                ET.SubElement(qrcResource, "file").text = resource
                # this is the QML file, which is the name for the qrc file as well
                componentName = resource.replace(".qml", "")
            else:
                os.chdir(resource)
                for subResource in sorted(os.listdir(".")):
                    ET.SubElement(qrcResource, "file").text = resource + "/" + subResource
                os.chdir("..")
        
        tree = ET.ElementTree(qrcRoot)
        tree.write(componentName + ".qrc", encoding="utf-8", xml_declaration=True)
        qrcList.append(model + "/" + componentName + ".qrc")
        os.chdir("..")

    # append the QRC file to the .pro file
    f = open("lightBaking.pro", "a", encoding='utf-8')
    f.write("!ios {\n")

    if len(qrcList) > 0:
        f.write("\tRESOURCES += \\\n")

    for qrc in qrcList:
        if ' ' in qrc:
            qrc = '"' + qrc + '"' 
        f.write("\t\t" + qrc + " \\\n")
    f.write("} #!ios\n")
    f.close()

    os.chdir(original_dir)

def generate_tests(directory, blacklist):
    original_dir = os.getcwd()
    os.chdir(directory)
    models = {}
    for model in sorted(os.listdir(".")):
        if not os.path.isdir(model):
            continue
        if model in blacklist:
            continue
        os.chdir(model)
        model_contents = os.listdir(".")
        gltf_variant_dirs = [d for d in model_contents if d.startswith("glTF")]

        for variant_dir in gltf_variant_dirs:
            # assimp v5.2.5 cannot support buffer descriptions
            if variant_dir == 'glTF-Meshopt' or variant_dir == 'glTF-Draco':
                continue
            model_file = [f for f in os.listdir(variant_dir)
                          if f.endswith(".glb") or f.endswith(".gltf")][0]
            os.chdir(variant_dir)
            models[model] = os.getcwd() + os.path.sep + model_file
            os.chdir("..")
            break # only handle the first found
        os.chdir("..")

    os.chdir(original_dir)
    return models

def generate_test_list(output_dir):
    original_dir = os.getcwd()
    os.chdir(output_dir)
    tests = {}
    for test in sorted(os.listdir(".")):
        if not os.path.isdir(test):
            continue
        os.chdir(test)
        # Get the component name
        components = [f for f in os.listdir(".")
                      if f.endswith(".qml")]
        if not components:
            continue
        tests[test] = test + "/" + components[0]
        os.chdir("..")
    os.chdir(original_dir)
    return tests

def populate_blacklist():
    blacklist = []
    f = open("blacklist.txt", "r", encoding='utf-8')
    for line in f:
        if line.startswith("#"):
            continue
        blacklist.append(line.strip())
    f.close()
    return blacklist

def append_root_properties(model_name, buf):
    find = "id: node"
    root_properties =\
    "\n\n\tproperty bool bakingEnabled: true\n\
    property int lightmapBaseResolution: 256"

    if not find in buf:
        print(f"Could not find root node identifier '{find}' in {model_name}.")
        return buf
    
    return buf.replace(find, find + root_properties, 1)

def append_baked_lightmap(model_name, buf):
    find = "Model {"
    model_lightmap_template = (
        "usedInBakedLighting: node.bakingEnabled\n"
        "lightmapBaseResolution: node.lightmapBaseResolution\n"
        "bakedLightmap: BakedLightmap {\n"
        "\tenabled: node.bakingEnabled\n"
        "\tkey: \"$\"\n"
        "\tloadPrefix: \"file:\"\n"
        "}"
    )

    updated_buf = []
    lines = buf.splitlines()
    models_found = 0
    models_patched = 0

    for i, line in enumerate(lines):
        updated_buf.append(line)

        # Find all lines starting with 'Model {', extract ID and append the template updated with key: ID
        if line.strip().startswith(find):
            models_found += 1
            if i + 1 < len(lines):
                match = re.match(r"(\s*)id:\s*([\w\d_]+)", lines[i + 1])  
                if match:
                    indentation = match.group(1)
                    model_id = match.group(2)
                    indented_lightmap_properties = "\n".join(
                        indentation + line for line in model_lightmap_template.splitlines()
                    )
                    lightmap_properties = indented_lightmap_properties.replace("$", f"{model_name}_{model_id}")
                    updated_buf.append(lightmap_properties)
                    models_patched += 1
                else:
                     print(f"No 'id:' found for {model_name}.")

    if (models_patched != models_found):
        print(f"Failed to patch all models in {model_name}: Managed {models_patched}/{models_found}.")
    
    return "\n".join(updated_buf)

# Modifies all tests to include root properties for lightmap baking and bakedLightmap property to each Model
def add_lightmap_baking_properties(output, tests):
    for model in tests:
        file = output + os.path.sep + tests[model]
        with open(file, "r+", encoding="utf-8") as f:
            buf = f.read()
            buf = append_root_properties(model, buf)
            buf = append_baked_lightmap(model, buf)
            f.seek(0)
            f.write(buf)
            f.truncate()

# Run a command and print stderr on error (non-zero return value)
def run_command(cmd):
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        print("Command failed: " + " ".join(cmd))
        print(result.stderr.decode("utf-8").strip())

# Main function start
if __name__ == '__main__':
    # Get source directory (should be the location of this __file__)
    original_dir = os.getcwd()
    template_source_dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(template_source_dir)

    parser = ArgumentParser()
    parser.add_argument("-o", "--output", dest="output",
                        help="Directory to write Output", metavar="OUTPUT")
    parser.add_argument("-b", "--balsam", dest="balsam",
                        help="Location of balsam tool", metavar="BALSAM")
    parser.add_argument("-i", "--input", dest="input",
                        help="Location of source directory", metavar="INPUT")

    args = parser.parse_args()

    blacklist = populate_blacklist()
    # Generate QML from GLTF2 files
    models = generate_tests(args.input, blacklist)
    print(f"Found {len(models)} eligible model files")

    # create output folder if it doesn't exist
    if not os.path.exists(args.output):
        os.makedirs(args.output)

    copy_template_files(args.output)

    cmds = []
    print("Running balsam on models...")
    for model in models:
        output_path = args.output + os.path.sep + model + os.path.sep
        cmd = [args.balsam, "--generateLightmapUV", "-o", output_path, models[model]]
        cmds.append(cmd)
    Pool().map(run_command, cmds)
    
    tests = generate_test_list(args.output)
    print(f"Balsam successfully generated {len(tests)}/{len(models)} files")
    generate_qrc_files(args.output)
    
    print("Patching baking properties...")
    add_lightmap_baking_properties(args.output, tests)

    os.chdir(original_dir)
    print("Done")
