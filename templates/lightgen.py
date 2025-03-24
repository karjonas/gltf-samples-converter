#!/usr/bin/env python
import json
import subprocess
import os
from argparse import ArgumentParser
import tempfile
from pathlib import Path
import shutil
import glob

def run_command(cmd):
    result = subprocess.run(cmd, check=True)
    if result.returncode != 0:
        print("Command failed: " + " ".join(cmd))
        print(result.stderr.decode("utf-8").strip())


def convert_value(val):
    """Attempt to convert a string override value to bool, int, or float if appropriate."""
    if isinstance(val, str):
        if val.lower() == "true":
            return True
        if val.lower() == "false":
            return False
        if val.isdigit():
            return int(val)
        try:
            return float(val)
        except ValueError:
            return val
    return val

def parse_overrides(override_tokens):
    """
    Parse unknown command-line tokens (e.g. '--key value' or '--key=value')
    and return a dictionary of overrides.
    """
    overrides = {}
    i = 0
    while i < len(override_tokens):
        token = override_tokens[i]
        if token.startswith("--"):
            token = token[2:]
            if "=" in token:
                key, val = token.split("=", 1)
            else:
                key = token
                if i + 1 < len(override_tokens) and not override_tokens[i + 1].startswith("--"):
                    i += 1
                    val = override_tokens[i]
                else:
                    val = "true"
            overrides[key] = convert_value(val)
        i += 1
    return overrides

def load_config(config_path, model_path, cmd_overrides=None):
    """
    Load the JSON config from file, optionally override the model key and merge model-specific
    overrides from the JSON, then apply command-line overrides.
    """
    with open(config_path, "r") as f:
        config_data = json.load(f)
    
    config_data["model"] = Path(model_path).as_uri()

    if cmd_overrides:
        config_data.update(cmd_overrides)
    
    return config_data

def write_temp_config(config_data):
    """
    Write the config data to a temp file and return the file path
    """
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tmp_file:
        json.dump(config_data, tmp_file, indent=4)
        tmp_file.flush()
        os.fsync(tmp_file.fileno())
        tmp_file_path = os.path.abspath(tmp_file.name)
    # Debug: Print out the temporary file path and its contents.
    # print("Temporary config file written to:", tmp_file_path)
    # with open(tmp_file_path, "r") as f:
        # print("Temporary file contents:")
        # print(f.read())
    return tmp_file_path

def get_available_models(path):
    result = {}
    for subdir in Path(path).iterdir():
        if subdir.is_dir():
            qml_list = list(subdir.rglob('*.qml'))
            if len(qml_list) == 1:
                qml_file = qml_list[0]
                result[qml_file.stem] = str(qml_file.resolve())
            elif len(qml_list) == 0:
                print(f"Warning: No .qml file found in {subdir}")
            else:
                print(f"Warning: Multiple .qml files found in {subdir}")
    return result

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("-q", "--qml", dest="qml", help="Path to qml executable", metavar="QML")
    parser.add_argument("-i", "--input", dest="input", help="Path to model file(s)", metavar="INPUT")
    parser.add_argument("-c", "--config", dest="config", help="Path to config file", metavar="CONFIG")
    parser.add_argument("-m", "--models", dest="models",
                    help="List of models to bake, must be comma separated. Bakes all if none provided", metavar="MODELS")
    parser.add_argument("-list", dest="list", help="List all models available", action='store_true')
    parser.add_argument('--bake', dest='bake', action='store_true')

    args, unknown = parser.parse_known_args()

    all_models = get_available_models(args.input)
    if len(all_models) == 0:
        print(f"No models found at {args.input}")
        exit(0)

    cmd_overrides = parse_overrides(unknown)
    
    if args.list:
        print(f"Found {len(all_models)} models:\n{", ".join(all_models)}")
        exit(0)

    if not args.qml or not os.path.exists(args.qml):
        print(f"Not valid QML executable")
        exit(1)

    if not args.config or not os.path.exists(args.config):
        print(f"Not valid config path")
        exit(1)

    final_models = {}
    if args.models:
        arg_models =  [m.strip() for m in args.models.split(',')]
        for model in arg_models:
            if model in all_models:
                final_models[model] = all_models[model]
    else:
        final_models = all_models

    if len(final_models) == 0:
        print("No models to bake. Exiting")
        exit(0)

    os.environ["QML_XHR_ALLOW_FILE_READ"] = str(1) # To allow QML to access a local file

    for model in final_models:
        config_data = load_config(args.config, final_models[model], cmd_overrides)
        tmp_file_path = write_temp_config(config_data)
        tmp_file_url = Path(tmp_file_path).as_uri()
        cmd = [args.qml, "Main.qml", "--", tmp_file_url]
        if args.bake:
            cmd.append("--bake-lightmaps")
        
        if not args.bake:
            try:
                src=f"qlm_multipart_{model}.exr"
                dst="qlm_multipart.exr"
                shutil.copy2(src,dst)
            except Exception as e:
                print(f"Failed to find qlm_multipart.exr for model {model}. Probably not baked yet.")

        run_command(cmd)

        if args.bake:
            try:
                src="qlm_multipart.exr"
                dst=f"qlm_multipart_{model}.exr"
                shutil.copy2(src,dst)
            except Exception as e:
                print(f"Failed to find qlm_multipart.exr for model {model}. Probably failed to bake.")

        try:
            os.remove(tmp_file_path)
        except Exception as e:
            print(f"Failed to delete temp file: {e}")
