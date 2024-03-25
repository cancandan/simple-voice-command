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

## How it works?
When you start the app to recognize your voice, it opens the input audio stream from the input device specified in the configuration file and starts monitoring the RMS of the chunks of signal. When this exceeds a threshold it is considered as voice activity. The capturing of your utterance can be tuned by the configuration paramaters detailed in the next section. Once your utterance is captured, it computes its MFCC(https://en.wikipedia.org/wiki/Mel-frequency_cepstrum) and find its distance to the MFCCs of all the recorded commands by [Dynamic Time Warping (DTW)](https://en.wikipedia.org/wiki/Dynamic_time_warping). The results are sorted by distance. If the top three distances agree it considers it as recognized, otherwise it reports that it is unsure.
