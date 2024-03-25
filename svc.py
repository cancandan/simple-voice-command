import wave
import sys
import os
import pyaudio
import numpy as np 
from collections import deque, defaultdict
import click
import glob
import configparser
import librosa
import contextlib
import re
import pickle
import pathlib 
from dtw import *
import subprocess


# Silence pyaudio stderr
@contextlib.contextmanager
def ignore_stderr():
    # yield
    devnull = os.open(os.devnull, os.O_WRONLY)
    old_stderr = os.dup(2)
    sys.stderr.flush()
    os.dup2(devnull, 2)
    os.close(devnull)
    try:
        yield
    finally:
        os.dup2(old_stderr, 2)
        os.close(old_stderr)

def read_config():
    config = configparser.ConfigParser(allow_no_value=True)
    config.read("config.ini")
    return config

class LiveProcessor():
    def __init__(self, config):
        self.config = config
        self.audiobuf = deque([])
        self.rmsthresh = float(self.config['PARAMS']['rms_threshold'])
        self.speaking = False
        self.redemptionCounter = 0
        self.redemption_frames = int(self.config['PARAMS']['redemption_frames'])
        self.min_speech_frames = int(self.config['PARAMS']['min_speech_frames'])
        self.preSpeechPadFrames = int(self.config['PARAMS']['prepad_frames'])

        self.mfccs = None
        self.label2cmd = None
        self.file_labels = None
        self.doclassify = False
    
        self.n_mfcc = int(self.config['PARAMS']['n_mfcc'])
        self.CHUNK = int(self.config['PARAMS']['CHUNK'])
        self.CHANNELS = int(self.config['PARAMS']['CHANNELS'])
        self.RATE = int(self.config['PARAMS']['RATE'])

        self.input_device_index = int(self.config['PARAMS']['input_device_index'])
        self.output_device_index = int(self.config['PARAMS']['output_device_index'])
        self.FORMAT = pyaudio.paInt16

        self.p = None
        self.out_stream=None
        self.inp_stream=None
    
    def play(self, p, record):        
        self.openOutput()
        self.out_stream.write(record.tobytes())
       
    def classify(self, record):    
        mfcc = librosa.feature.mfcc(y=record, sr=self.RATE, n_mfcc=self.n_mfcc)
        distanceTest = []
        for m in self.mfccs:
            dist = dtw(mfcc.T, m.T, dist_method='euclidean', distance_only=True, step_pattern='asymmetric').normalizedDistance
            distanceTest.append(dist)
        
        zipped = [x for x in zip(self.file_labels, distanceTest)]
        zipped = sorted(zipped, key=lambda x:x[1])
        top3 = set([x[0] for x in zipped[:3]])
        if len(top3)>2:
            print("unsure")
        else:
            print(f"Recognized as '{self.label2cmd[zipped[0][0]]}', running executable {self.label2cmd[zipped[0][0]]}.sh")
            subprocess.run([f'./{self.label2cmd[zipped[0][0]]}.sh']) 

    def openOutput(self):        
        self.createPyaudio()
        if not self.out_stream:
            self.out_stream = self.p.open(input_device_index=self.input_device_index, output_device_index=self.output_device_index, format=self.FORMAT, channels=self.CHANNELS, rate=self.RATE, output=True)#, frames_per_buffer=self.CHUNK)

    def createPyaudio(self):
        if not self.p:
            self.p = pyaudio.PyAudio()

    def openInput(self):          
        self.createPyaudio()
        if not self.inp_stream:
            self.inp_stream = self.p.open(input_device_index=self.input_device_index, output_device_index=self.output_device_index, format=self.FORMAT, channels=self.CHANNELS, rate=self.RATE, input=True, frames_per_buffer=self.CHUNK)

    def start(self):
        self.createPyaudio()
        self.openInput()

        burnin = 0
        
        while True:                                                     
            data = self.inp_stream.read(self.CHUNK, exception_on_overflow=False)
            if burnin < 50:
                burnin += 1
                continue
            if burnin==50:
                burnin += 1
                click.echo("Started listening...")

            data = np.frombuffer(data, dtype=np.int16)
            
            d = data.astype(np.float32)
            rms = np.sqrt( np.mean(d**2) )
            exceedThresh = (rms > self.rmsthresh) * 1.0
            self.audiobuf.append({'data':data,'exceedThresh':exceedThresh})
            
            if exceedThresh and self.redemptionCounter!=0:
                self.redemptionCounter = 0

            if exceedThresh and not self.speaking:
                self.speaking = True
                print("rms threshold exceeded, assuming this is speech")

            if not exceedThresh and self.speaking:
                self.redemptionCounter+=1
                if self.redemptionCounter > self.redemption_frames:
                    self.redemptionCounter = 0
                    self.speaking = False
                     
                    totspeech = 0
                    for x in self.audiobuf:
                        totspeech+=x.get("exceedThresh")
                    if totspeech > self.min_speech_frames:
                        conc = []
                        for x in self.audiobuf:
                            conc.append(x.get('data'))
                        result = np.concatenate(conc)
                        sampsize = self.p.get_sample_size(self.FORMAT)
                        if self.doclassify:
                            self.classify(result.astype(np.float32)/(2**15))
                            continue
                        self.play(self.p, result)
                        return sampsize, result
                    else:
                        print("less than minimum speech frames setting, flagging as misfire\n")

            if not self.speaking:
                while len(self.audiobuf) > self.preSpeechPadFrames:
                    self.audiobuf.popleft()

def add_audio_to_command(num, name, config):
    while True:
        click.echo(f"{num}. Say the command \"{name}\" after it starts listening..")
        l = LiveProcessor(config)
        with ignore_stderr():
            sampsize, result = l.start() 
        
        if click.confirm(f"Replayed what you said, does it sound ok?", default=True):
            files = glob.glob(f"{name}_*.wav")
            current = 1+len(files)
            with wave.open(f"{name}_{current}.wav", 'wb') as wf:
                wf.setnchannels(l.CHANNELS)
                wf.setsampwidth(sampsize)
                wf.setframerate(l.RATE)
                wf.writeframes(result.tobytes())
            break    


@click.group()
def main():
    pass

from scipy.io import wavfile
@main.command()
def sound_check():    
    config = read_config()
    click.echo("Speak after you see \"Started listening...\" Your speech will be replayed.\nCheck that there is no clipping at the beginning, middle or end.\nIf there is, you need to make sure this does not happen by changing the parameters discussed in the documentation.\nExit by sending CTRL-C\n")
    
    file_names = glob.glob("*_*.wav")
    rmses = []
    for f in file_names:
        sr, data = wavfile.read(f)
        data = data.astype(np.float32)
        rmses.append(np.sqrt(np.mean(data**2)))
    if len(rmses)>0: 
        print(f"Mean RMS of audio examples recorded so far: {np.mean(np.array(rmses))}")


    while True:
        with ignore_stderr():
            l = LiveProcessor(config)
            sampsize, data = l.start()
            data = data.astype(np.float32)
            print(f"RMS of this recording: {np.sqrt(np.mean(data**2))} Make sure this is on the same ballpark as the average RMS shown above by adjusting microhpne volume.")
           
@main.command()
def add_command():    
    config = read_config()
    while True:
        file_names = glob.glob("*_*.wav")
        cmd2count = defaultdict(lambda: 0)
        for f in file_names:
            m = re.match("(.*)_(.*).wav", f)
            name = m.group(1)
            count = m.group(2)
            if name and count:
                count = int(count)
                if count > cmd2count[name]:
                    cmd2count[name]=count
                
        name = click.prompt(f"Enter a name for the command")
        acount = cmd2count.get(name, 0)
        while True:
            acount += 1
            add_audio_to_command(acount,name,config)
            another = click.prompt("Add another audio to command?", default=True)
            if not another:
                break

        anotherCmd = click.prompt("Add another command?", default = True)
        if not anotherCmd:
            break

@main.command()
def io_select():
    
    p = pyaudio.PyAudio()
    devices = p.get_device_count()
    dmicidx = p.get_default_host_api_info()['defaultInputDevice']
    
    click.echo("\n\nList of possible devices for sound input:\n")
    for i in range(devices):
        device_info = p.get_device_info_by_index(i)
        
        if device_info.get('maxInputChannels') > 0:
            if dmicidx == i:
                click.echo(f"*** default device *** device index: {i} name: {device_info.get('name')} SR:{device_info.get('defaultSampleRate')}")
            else:
                click.echo(f"device index: {i} name: {device_info.get('name')} SR:{device_info.get('defaultSampleRate')}")

    click.echo("")    
    selmic = click.prompt("Enter selected input device idx (or enter for default)", type=click.INT, default=dmicidx)
    click.echo(f"selected {selmic}")


    doutidx = p.get_default_host_api_info()['defaultOutputDevice']
    
    click.echo("\n\nList of possible devices for sound output:\n")
    for i in range(devices):
        device_info = p.get_device_info_by_index(i)
        
        if device_info.get('maxOutputChannels') > 0:
            if doutidx == i:
                click.echo(f"*** default device *** device index: {i} name: {device_info.get('name')} SR:{device_info.get('defaultSampleRate')}")
            else:
                click.echo(f"device index: {i} name: {device_info.get('name')} SR:{device_info.get('defaultSampleRate')}")

    click.echo("")    
    selout = click.prompt("Enter selected output device idx (or enter for default)", type=click.INT, default=doutidx)
    click.echo(f"selected {selout}")

    config = read_config()
    config["PARAMS"]['input_device_index']=str(selmic)
    config['PARAMS']['output_device_index']=str(selout)
    with open("config.ini", 'w') as f:
        config.write(f)

def get_file_infos():
    info = {}   
    for x in pathlib.Path('.').glob("*_*.wav"):
        try:
            info[str(x)] = x.stat().st_ctime
        except FileNotFoundError:
            pass
    
    return info

@main.command()
def recognize():
    config = read_config()
    
    label2cmd = None
    mfccs = None
    recent_infos = None
    file_names = None
    file_labels = None

    modelFile = pathlib.Path("model")
    rebuildModel = False
  
    if modelFile.is_file():
        file = open("model", 'rb')
        model = pickle.load(file)
        recent_infos = get_file_infos()
        if model['file_infos'] != recent_infos:
            rebuildModel = True
        else:
            mfccs = model['mfccs']
            label2cmd = model['label2cmd']
            file_names = model['file_names']
            file_labels = model['file_labels']

    else:
        rebuildModel = True
    
    if rebuildModel:
        click.echo("Rebuilding model, please wait..")
        label2cmd = {}
        cmd2label = {}
    
        file_names = glob.glob("*_*.wav")
        total_files = len(file_names)
        file_labels = np.zeros(total_files)
        mfccs = []
        command_names = set()
        for i, f in enumerate(file_names):
            m = re.match("(.*)_(.*).wav", f)
            name = m.group(1)  
            command_names.add(name)

            y1, sr1 = librosa.load(f,sr=None)
            mfcc1 = librosa.feature.mfcc(y=y1, sr=int(config['PARAMS']['rate']), n_mfcc=int(config['PARAMS']['n_mfcc']))
            mfccs.append(mfcc1)

        command_names = sorted(command_names)   
        for i,n in enumerate(command_names):
            label2cmd[i]=n
            cmd2label[n]=i         
        
        for i, f in enumerate(file_names):
            m = re.match("(.*)_(.*).wav", f)
            name = m.group(1)
            file_labels[i]= cmd2label[name]

        modelPickle = open('model', 'wb')
        model = {'mfccs':mfccs, 'file_labels':file_labels, 'file_infos':recent_infos,
                 'file_names':file_names, 'label2cmd':label2cmd}
        pickle.dump(model, modelPickle)
        modelPickle.close() 

    l = LiveProcessor(config)
    l.doclassify=True
    l.label2cmd = label2cmd
    l.file_labels=file_labels
    l.mfccs = mfccs
    with ignore_stderr():
        l.start()

if __name__=="__main__": 
    main()
