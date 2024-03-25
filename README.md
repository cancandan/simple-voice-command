# simple-voice-command
language agnostic, small footprint, simple voice recognition 


## What is this?
This is a command line python application for recognizing voice commands and executing actions associated with them.    

## How to run?
1. Clone this repository to your machine and change directory to where you have cloned.
2. Make a virtual environment by following the [official instructions](https://docs.python.org/3/library/venv.html), and activate it.
3. Install the required libraries by `pip install -r requirements.txt`
4. Run `python svc.py io-select` and follow instructions to check and set input and output device
5. Run `python svc.py sound-check` and follow instructions to test that you are able to cleanly record your voice. You may need to adjust your mic levels.
6. Run `python svc.py add-command` and follow instructions to add voice commands
7. Make a shell script with the command name, for example, if you have added a command called `open`
   Make a shell script named `open.sh` with contents like this:
   ```
   #!/bin/sh
   echo "open command example"
   ```
   Then make it executable via `chmod +x open.sh`
9. Run `python svc.py recognize` to start the app that will listen for your voice, recognize what you say and execute the associated command.
