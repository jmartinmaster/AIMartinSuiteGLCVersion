#!/bin/bash

# Navigate to the project directory
cd /home/jamie/Documents/AI-Martin/AIMartinSuiteGLCVersion

# Activate the virtual environment
source .venv/bin/activate

# Run the Python program
nohup python main.py > /dev/null 2>&1 &