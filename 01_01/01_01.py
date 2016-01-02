#! usr/bin/env python2.7

import librosa
import vamp
import os
import pandas as pds

def load_audio_file(fpath):
    '''Takes complete path to an audio file. Returns data, rate of loaded audio file (as mono)'''
    data, rate = librosa.load(fpath, mono=True)
    return data, rate

def choose_vamp_plugin():
    '''Takes nothing, returns a user-chosen vamp plugin'''
    print 'Choose a vamp plugin to use to analyze audio data:\n'
    for index, value in enumerate(vamp.list_plugins()):
        print '%d: %s' % (index, value)
    choice = int(raw_input('Enter the number corresponding to the desired vamp plugin: '))
    return vamp.list_plugins()[choice]

def parse_note_transcription_output(plugin_output):
    '''Takes plugin output dictionary (assumed UA note transcription plugin used), returns note_start_lst, dur_lst, note_lst (in that order)'''
    note_start_lst = []
    dur_lst = []
    note_lst = []
    for entry in plugin_output['list']:
        note_start_lst.append(entry['duration'])
        dur_lst.append(entry['timestamp'])
        note_lst.append(int(entry['values'][0]))
    return note_start_lst, dur_lst, note_lst

def make_note_dataframe(note_start_lst, dur_lst, note_lst):
    '''Takes note_start_lst, dur_lst, note_lst, audio_data, returns pandas dataframe of note occurrences, where notes are sorted from lowest to highest and shortestduration to longest'''
    # make a nested_note_dict. structure: keys are midi note values. values are
    #   dictionaries with keys referring to counts of that note, values a dictionary of 'start time' and 'duration'
    note_counts = {}
    nested_note_dict = {}
    for index, value in enumerate(note_lst):
        if value not in note_counts:
            note_counts[value] = 0
            nested_note_dict[value] = {}
            nested_note_dict[value][note_counts[value]] = {'start time': note_start_lst[index], 'duration': dur_lst[index]}
        else:
            note_counts[value] += 1
            nested_note_dict[value][note_counts[value]] = {'start time': note_start_lst[index], 'duration': dur_lst[index]}
    # convert nested_note_dict to pandas dataframe, like Wouter's Stack Exchange answer in 'Construct pandas DataFrame from items in nested dictionary'
    notes = []
    frames = []
    for note, d in nested_note_dict.iteritems():
        notes.append(note)
        from_dict_frame = pds.DataFrame.from_dict(d, orient='index')
        from_dict_frame.sort(columns='duration', ascending=True, inplace=True)
        frames.append(from_dict_frame)
    notes, frames = (list(x) for x in zip(*sorted(zip(notes, frames), key=lambda pair: pair[0])))
    note_df = pds.concat(frames, keys=notes)
    return note_df

def make_reordered_wav_file(audio_data, rate, note_df):
    '''Takes audio_data, rate, note_df (sorted note_df from make_note_dataframe, for instance), sorts audio segments in order specified by note_df, writes wav file.'''
    print 'Curent dir is %s.' % os.getcwd()
    os.chdir(raw_input('Enter the desired directory to place the wav files in: '))
    intervals_lst = []
    for row in note_df.itertuples():
        print row
        start_samp = librosa.core.time_to_samples(float(row[1]))[0]
        end_samp = librosa.core.time_to_samples(float(row[2])+float(row[1]))[0]
        intervals_lst.append((start_samp, end_samp))
        print "start: %r. end: %r" % (start_samp, end_samp)
    reordered_audio_data = librosa.effects.remix(audio_data, intervals_lst, align_zeros=False)
    librosa.output.write_wav(raw_input('Enter desired filename: '), reordered_audio_data, rate)

def main():
    fpath = raw_input('Enter full path to audio file: ')
    data, rate = librosa.load(fpath)
    plugin_choice = choose_vamp_plugin()
    # this script is assuming that university of alicante polyphonic transcription is being used
    num_voices = int(raw_input('Enter desired number of voices: '))
    plugin_output = vamp.collect(data, rate, plugin_choice, parameters={'maxpolyphony':num_voices})
    note_start_lst, dur_lst, note_lst = parse_note_transcription_output(plugin_output)
    print 'note_start_lst length: %d, dur_lst length: %d, note_lst length: %d.' % (len(note_start_lst), len(dur_lst), len(note_lst))
    note_df = make_note_dataframe(note_start_lst, dur_lst, note_lst)
    print note_df
    make_reordered_wav_file(data, rate, note_df)

if __name__ == '__main__':
    main()
