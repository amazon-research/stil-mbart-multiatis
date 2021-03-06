# preprocess_atis_traditional.py
# Copyright Amazon.com Inc. or its affiliates
# Jack FitzGerald - jgmf@amazon.com

"""
This script pull in the training, dev, and test data for MultiATIS++
It outputs **un**translated, slotted data with intent and language ID
Assumes input file is SPLIT_LANG.tsv. EX: dev_DE.tsv
Input files from MultiATIS++ are: id | utterance | slot labels | intent
Input files from MulitATIS are: id | English utterance | English annotations
... | machine translation back to English |intent | non-English utterance
... | non-English annotations
"""

import os
import argparse
import csv
import logging

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s',
    level=logging.INFO,filename='atis_preprocess.log', filemode='w')

def data_import_mapp(args):
    """
    imports the the raw data from the MultiATIS++ files

    Arguments:
        args: the ArgumentParser object

    Returns:
        all_data: A python dict (lang) of dicts (split) of dicts (ID) with the
                  raw data.
        langs: Python list of the ingested languages
        nonenglish_langs: Python list of ingested languages minus English
    """

    file_names = []

    # iterate through all the files
    for _root, _dirs, files in os.walk(args.input_path_mapp):

        if files:
            for filename in files:
                file_names.append(filename)

    # outer dictionary, all_data, uses language as a key.
    # the middle dictionary uses split as a key
    # the inner dictionary uses id as a key.
    # the values of the inner dictionary are lists containing utterance,
    # ... slots, and intent
    # EX: all_data['DE']['test'][4489] = ['GÃƒÆ’Ã‚Â¼nstigster Flugpreis von
    # ... Tacoma nach Orlando', 'B-cost_relative O O B-fromloc.city_name O
    # ... B-toloc.city_name', 'atis_airfare']

    all_data = {}

    for filename in file_names:
        if filename:
            with open(os.path.join(args.input_path_mapp, filename),"r") as f:
                # extract info from file name
                split, lang_ext = filename.split('_')
                lang, _ext = lang_ext.split('.')
                lang = lang.lower()
                _foo = all_data.setdefault(lang, {})
                _foo = all_data[lang].setdefault(split, {})

                # Pull in data line by line
                reader = csv.reader(f, delimiter='\t')
                next(reader)
                for row in reader:
                    eye_d, utterance, slots, intent = row[0], row[1], row[2], \
                        row[3]
                    intent = intent.replace('atis_','')
                    all_data[lang][split][int(eye_d)] = [utterance, slots,
                        intent]

    # This is hard coded. Change if making this code generic
    logging.info('Example entry for all-data dictionary %s',
        str(all_data['de']['test'][1007]))

    langs = [key for key in all_data.keys()]
    print('\nProcessed the following languages from MultiATISpp: ')
    print(langs)

    logging.info('number of samples in de train: %s',
        str(len(all_data['de']['train'])))

    return all_data, langs

def reformat_data_mapp(all_data, langs):
    """
    Aligns the MultiATIS++ non-English and English data and formats as a
    sequence like "fluge von salt lake city nach oakland kalifornien" as input
    and "salt <B-fromloc.city name> lake <I-fromloc.city name> city-
    <I-fromloc.city name> oakland <B-toloc.city name> california-
    <B-toloc.state name> <intent-flight> <lang-de>" as output

    Arguments:
        all_data: A python dict (lang) of dicts (split) of dicts (ID) with the
                  raw data.
        langs: Python list of the ingested languages

    Returns:
        final_data : Python dict (input vs output) of dicts (split) containing
                     lists of the formatted data as strings
    """
    final_data = dict.fromkeys(['input', 'output'])

    # initialize
    for key in final_data:
        final_data[key] = dict.fromkeys(['train', 'dev', 'test'])
        final_data[key]['train'], final_data[key]['dev'], \
            final_data[key]['test'] = [], [], []

    # iterate through and reformat the string of each example
    for lang in langs:
        for split, lang_split_dict in all_data[lang].items():
            for _eye_d, sample_data in lang_split_dict.items():
                utt = sample_data[0].lower()
                outstr = ''
                for token, slot in zip(utt.split(), sample_data[1].split()):
                    if slot != 'O':
                        outstr = outstr + token + ' ' + '<' + slot + '>' + ' '
                outstr = outstr+'<intent-'+sample_data[2]+'> <lang-'+lang+'>'
                final_data['input'][split].append(utt)
                final_data['output'][split].append(outstr)

    # Examples arbitrarily chosen and hard coded. May need to change later.
    print('\nThree examples across train, dev, test:')

    print(''.join(['\n\n\033[1m{0}:\033[0m {1}'\
        .format(k,v['train'][2]) for k,v in final_data.items()]))
    print(''.join(['\n\n\033[1m{0}:\033[0m {1}'\
        .format(k,v['dev'][2]) for k,v in final_data.items()]))
    print(''.join(['\n\n\033[1m{0}:\033[0m {1}'\
        .format(k,v['test'][2]) for k,v in final_data.items()]))

    return final_data

def get_hi_tr_dev_mapp(args):
    """
    imports the dev set utterances for hi and tr from MultiATIS++

    Arguments:
        args: the ArgumentParser object

    Returns:
        hi_tr_dev: Python list of the hi and tr dev utterances
    """

    # get the file names
    file_names, hi_tr_dev = [], {}
    hi_tr_dev['hi'], hi_tr_dev['tr'] = [], []

    for _root, _dirs, files in os.walk(args.input_path_hi_tr_dev):
        if files:
            for filename in files:
                file_names.append(filename)

    for filename in file_names:
        if filename:
            # add the data line by line
            with open(os.path.join(args.input_path_hi_tr_dev, filename),"r") as f:
                reader = csv.reader(f, delimiter='\t')
                next(reader)
                _split, lang_ext = filename.split('_')
                lang, _ext = lang_ext.split('.')
                lang = lang.lower()
                for row in reader:
                    hi_tr_dev[lang].append(row[1])
    logging.info('The hi and tr dev sets: %s', hi_tr_dev)

    return hi_tr_dev

# Import and add the data from MultiATIS
def data_import_ma(args, final_data, hi_tr_dev):
    """
    imports the MultiATIS data and adds it to the final_data object.
    Utterances from the MultiATIS++ hi_tr_dev list are put into the dev set

    Arguments:
        args: the ArgumentParser object
        final_data : Python dict (input vs output) of dicts (split) containing
                     lists of the formatted data as strings
        hi_tr_dev: Python list of the hi and tr dev utterances

    Returns:
        final_data : Python dict (input vs output) of dicts (split) containing
                     lists of the formatted data as strings
    """

    # get the file names
    file_names = []
    for _root, _dirs, files in os.walk(args.input_path_ma):
        if files:
            for filename in files:
                file_names.append(filename)

    for filename in file_names:
        if filename:
            with open(os.path.join(args.input_path_ma, filename),"r") as f:
                # extract info from file name
                lang, split_ext = filename.split('-')
                lang = 'hi' if lang == 'Hindi' else 'tr'
                split = split_ext.split('.', 1)
                split = str(split[0].split('_', 1)[0])
                logging.info('%s, %s', lang, split)

                # Pull in data line by line
                reader = csv.reader(f, delimiter='\t')
                for row in reader:
                    outstr = ''
                    intent, noneng_utt, noneng_slots = row[3], row[4], row[5]
                    intent = intent.replace('atis_','')

                    # iterate thru tokens and labels and add them
                    for token, slot in zip(noneng_utt.split(), noneng_slots.split()):
                        if slot != 'O':
                            outstr = outstr + token + ' <' + slot + '> '

                    # add intent and lang id
                    outstr = outstr + '<intent-' + intent + '> <lang-' + lang + '>'

                    if noneng_utt in hi_tr_dev[lang]:
                        final_data['input']['dev'].append(noneng_utt)
                        final_data['output']['dev'].append(outstr)
                        hi_tr_dev[lang].remove(noneng_utt)
                    elif (lang == 'hi') and (split == 'train'):
                        # basic 3x sampling for hindi train
                        for i in range(3):
                            final_data['input'][split].append(noneng_utt)
                            final_data['output'][split].append(outstr)
                    elif (lang == 'tr') and (split == 'train'):
                        # basic 7x sampling for turkish train
                        for i in range(7):
                            final_data['input'][split].append(noneng_utt)
                            final_data['output'][split].append(outstr)
                    else:
                        final_data['input'][split].append(noneng_utt)
                        final_data['output'][split].append(outstr)

    return final_data

def output_to_files(args, final_data):
    """
    out the data to 6 files, one for each split and input/output combo

    Arguments:
        args: the ArgumentParser object
        final_data : Python dict (input vs output) of dicts (split) containing
                     lists of the formatted data as strings

    Returns: Nothing
    """

    for inout, inner_dict in final_data.items():
        for split, data in inner_dict.items():
            with open(os.path.join(args.output_path, (split+"."+inout)), "w") as f:
                for line in data:
                    f.write(line)
                    f.write('\n')

def main():
    """ main """
    parser = argparse.ArgumentParser(description=\
        'Reformat the MultATIS++ data for Centurion Study D')
    parser.add_argument("input_path_mapp", help=\
        'the path of the MultiATIS++ data')
    parser.add_argument("input_path_ma", help=\
        'the path of the MultiATIS data')
    parser.add_argument("input_path_hi_tr_dev", help=\
        'the path of the hi and tr dev sets from MultiATIS++')
    parser.add_argument("output_path", help='the path for the output files')
    args = parser.parse_args()

    mapp_raw_data, langs = data_import_mapp(args)
    mapp_data = reformat_data_mapp(mapp_raw_data, langs)
    hi_tr_dev = get_hi_tr_dev_mapp(args)
    data = data_import_ma(args, mapp_data, hi_tr_dev)
    output_to_files(args, data)

if __name__ == "__main__":
    main()
