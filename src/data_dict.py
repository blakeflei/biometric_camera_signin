# Script to save the hmis FY 2020 v1.7 to a json file 
# for reference in the database and output

import json
import configparser

fn_config = 'biometric.cfg'

config = configparser.ConfigParser()
config.read(fn_config)
fn_datadict = config['DEFAULT']['fn_datadict']

# List tables:
data_dict = {'hmis_version': 'hmis fy2020 1.7',
             '1.6': {'name': 'RaceNone',
                     'data': {8: "Client doesn't know",
                              9: 'Client refused',
                              99: 'Data not collected'}},
             '1.7': {'name': 'Yes/No/Missing',
                     'data': {0: 'No',
                              1: 'Yes',
                              99: 'Data not collected'}},
             '1.8': {'name': 'No/Yes/Reasons for Missing Data',
                     'data': {0: 'No',
                              1: 'Yes',
                              8: "Client doesn't know",
                              9: 'Client refused',
                              99: 'Data not collected'}},
             '3.01.5': {'name': 'NameDataQuality',
                        'data': {1: 'Full name reported',
                                 2: 'Partial, street name, or code name reported',
                                 8: "Client doesn't know",
                                 9: 'Client refused',
                                 99: 'Data not collected'}},
             '3.02.2': {'name': 'SSNDataQuality',
                        'data': {1: 'Full SSN reported',
                                 2: 'Approximate or partial SSN reported',
                                 8: "Client doesn't know",
                                 9: 'Client refused',
                                 99: 'Data not collected'}},
             '3.03.2': {'name': 'DOBDataQuality',
                        'data': {1: 'Full DOB reported',
                                 2: 'Approximate or partial DOB reported',
                                 8: "Client doesn't know",
                                 9: 'Client refused',
                                 99: 'Data not collected'}},
             '3.05.1': {'name': 'Ethnicity',
                        'data': {0: 'Non-Hispanic/Non-Latino',
                                 1: 'Hispanic/Latino',
                                 8: "Client doesn't know",
                                 9: 'Client refused',
                                 99: 'Data not collected'}},
             '3.06.1': {'name': 'Gender',
                        'data': {0: 'Female',
                                 1: 'Male',
                                 2: 'Trans Female (MTF or Male to Female)',
                                 3: 'Trans Male (FTM or Female to Male)',
                                 4: 'Gender non-conforming (i.e. not excluxively male or female)',
                                 8: "Client doesn't know",
                                 9: 'Client refused',
                                 99: 'Data not collected'}},
             'V1.11': {'name': 'MilitaryBranch',
                       'data': {1: 'Army',
                                2: 'Air Force',
                                3: 'Navy',
                                4: 'Marines',
                                6: 'Coast Guard',
                                8: "Client doesn't know",
                                9: 'Client refused',
                                99: 'Data not collected'}},
             'V1.12': {'name': 'DischargeStatus',
                       'data': {1: 'Honorable',
                                2: 'General under honorable conditions',
                                4: 'Bad conduct',
                                5: 'Dishonorable',
                                6: 'Under other than honorable conditions (OTH)',
                                7: 'Uncharacterized',
                                8: "Client doesn't know",
                                9: 'Client refused',
                                99: 'Data not collected'}}}

with open(fn_datadict, 'w') as f:
    json.dump(data_dict, f)
