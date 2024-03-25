## What is this?
This is a command line python application for recognizing voice commands and executing actions associated with them.    

## How to run?
1. Clone this repository to your machine and change directory to where you have cloned.
2. Make a virtual environment by following the [official instructions](https://docs.python.org/3/library/venv.html), and activate it.
3. Install the required libraries by `pip install -r requirements.txt`
4. Run `python svc.py io-select` and follow instructions to check and set input and output device
5. Adjust the `config.ini` file included in the repository as explained at the bottom of the page.
6. Run `python svc.py sound-check` and follow instructions to test that you are able to cleanly record your voice. You may need to revisit step 5 and restart to check. You may also need to adjust your mic levels. 
7. Run `python svc.py add-command` and follow instructions to add your voice commands. Try adding at least 3 audio examples.
8. Make a shell script with the command name, for example, if you have added a command called `open`
   Make a shell script named `open.sh` with contents like this:
   ```
   #!/bin/sh
   echo "open command example"
   ```
   Then make it executable via `chmod +x open.sh`
9. Run `python svc.py recognize` to start the app that will listen for your voice, recognize what you say and execute the associated command.

## How it works?
When you start the app to recognize your voice, it opens the input audio stream from the input device specified in the configuration file and starts monitoring the RMS of the chunks of signal. When this exceeds a threshold it is considered as voice activity. The capturing of your utterance can be tuned by the configuration paramaters detailed in the next section. Once your utterance is captured, it computes its [MFCC](https://en.wikipedia.org/wiki/Mel-frequency_cepstrum) and find its distance to the MFCCs of all the recorded commands by [Dynamic Time Warping (DTW)](https://en.wikipedia.org/wiki/Dynamic_time_warping). The results are sorted by distance. If the top three distances agree on the label more than once, it is considered as recognized, otherwise it reports that it is unsure.

## Configuration
Here is the sample configuration file and what the fields mean:
```
rms_threshold = 2000
redemption_frames = 18
min_speech_frames = 4
prepad_frames = 7
chunk = 1024
channels = 1
rate = 44100
n_mfcc = 40
input_device_index = 20
output_device_index = 20
```

`rms_threshold` is the threshold RMS value beyond which the captured audio is considered as signal and recording is started

`redemption_frames` After the recording has started we begin counting the number of frames (chunks) of audio that fall below the 
`rms_threshold`. If this number is more than `redemption_frames` we can stop capturing audio. 

`min_speech_frames` We also check that the number of frames exceeding `rms_threshold` is above `min_speech_frames` so that instantaneous noise is not considered as speech.

`prepad_frames` is the number of frames to include, in the final captured audio, before the threshold is exceeded

`chunk` is the number of samples to process in one IO op

`channels` is the number of channels the IO device is using, 1 is mono, 2 is stereo.

`rate` is the sample rate

`n_mfcc` is the number of MFC components to compute

`input_device_index` and `output_device_index` is the device id as reported by pyaudio lib.
