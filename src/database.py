import configparser
import datetime
import json

import pandas as pd
from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import create_engine
from sqlalchemy import func
from sqlalchemy.exc import DatabaseError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
fn_config = 'biometric.cfg'


class SignLog(Base):
    """
    Sqlalchemy ORM table for individuals who have signed in.
    """
    __tablename__ = 'signin'

    id = Column(Integer, primary_key=True)
    fr_id = Column(String(50))
    class_prob = Column(Float)
    time = Column(DateTime, default=datetime.datetime.now())
    first_time = Column(Integer)


class SignSS(Base):
    """
    Sqlalchemy ORM table for sign in starts and stops.
    """
    __tablename__ = 'startstop'

    start_time = Column(DateTime, primary_key=True)
    stop_time = Column(DateTime)


class Clients(Base):
    """
    Create sqlalchemy orm table for guests.
    """
    __tablename__ = 'clients'

    personal_id = Column(Integer, primary_key=True)
    fr_id = Column(String(50))
    first_name = Column(String(50))
    middle_name = Column(String(50))
    last_name = Column(String(50))
    name_suffix = Column(String(50))
    name_data_quality = Column(Integer)
    ssn = Column(String(9))
    ssn_data_quality = Column(Integer)
    dob = Column(Date)
    dob_data_quality = Column(Integer)
    am_ind_ak_native = Column(Integer)
    asian = Column(Integer)
    black_af_american = Column(Integer)
    native_hi_other_pacific = Column(Integer)
    white = Column(Integer)
    race_none = Column(Integer)
    ethnicity = Column(Integer)
    gender = Column(Integer)
    veteran_status = Column(Integer)
    year_entered_service = Column(Integer)
    year_separated = Column(Integer)
    world_war_ii = Column(Integer)
    korean_war = Column(Integer)
    vietnam_war = Column(Integer)
    desert_storm = Column(Integer)
    afganistan_oif = Column(Integer)
    iraq_oif = Column(Integer)
    iraq_ond = Column(Integer)
    other_theater = Column(Integer)
    military_branch = Column(Integer)
    discharge_status = Column(Integer)
    hmis_version = Column(String(32))
    date_created = Column(DateTime)
    date_updated = Column(DateTime)
    user_id = Column(String(32))
    date_deleted = Column(DateTime)


def hmisv17_newguestdiag(guest_meta, datadict_menu_rev):
    """
    Translate guest metadata from the new guest dialog into
    hmis2020 v1.7 format for storage into a compilant db.
    """
    if 'dob' in guest_meta.keys() and isinstance(guest_meta['dob'], str):
        # Convert dob into a datetime.date obj
        # if full dob reported:
        guest_meta['dob'] = datetime.datetime.strptime(guest_meta['dob'], '%m/%d/%Y').date()
        guest_meta['dob_data_quality'] = 1
        ## if Approx or partial
        #guest_meta['dob_data_quality'] = 2
        ## if client doesn't know
        #guest_meta['dob_data_quality'] = 8
        ## if client refused
        #guest_meta['dob_data_quality'] = 9

    if 'race' in guest_meta.keys():
        guest_meta['am_ind_ak_native'] = 0
        guest_meta['asian'] = 0
        guest_meta['black_af_american'] = 0
        guest_meta['native_hi_other_pacific'] = 0
        guest_meta['white'] = 0
        if guest_meta['race'] == "American Indian or Alaskan Native":
            guest_meta['am_ind_ak_native'] = 1

        if guest_meta['race'] == "Asian":
            guest_meta['asian'] = 1

        if guest_meta['race'] == 'Black':
            guest_meta['black_af_american'] = 1

        if guest_meta['race'] == "Native HI or Other Pacific Islander":
            guest_meta['native_hi_other_pacific'] = 1

        if guest_meta['race'] == "White":
            guest_meta['white'] = 1

        if guest_meta['race'] == "Doesn't know":
            guest_meta['race_none'] = 8

        if guest_meta['race'] == 'Refused':
            guest_meta['race_none'] = 9

        del guest_meta['race']
    else:
        guest_meta['race_none'] = 99

    if 'gender' in guest_meta.keys():
        guest_meta['gender'] = datadict_menu_rev['3.06.1']['data'][guest_meta['gender']]

    if 'ethnicity' in guest_meta.keys():
        guest_meta['ethnicity'] = datadict_menu_rev['3.05.1']['data'][guest_meta['ethnicity']]

    if 'date_created' not in guest_meta.keys():
        guest_meta['date_created'] = datetime.datetime.now().date()

    if 'first_time' in guest_meta.keys():
        # Convert 'yes/no' to bool that sqlite can read
        guest_meta['first_time'] = {'Yes': 1, 'No': 0}[guest_meta['first_time']]

    guest_meta['ssn'] = ''

    # Data Quality Estimations:
    if guest_meta['middle_name'] != '' and guest_meta['last_name'] != '':
        guest_meta['name_data_quality'] = 1
    if guest_meta['middle_name'] == '' or guest_meta['last_name'] == '':
        guest_meta['name_data_quality'] = 2
    if "don't know" in guest_meta['first_name'].lower():
        guest_meta['name_data_quality'] = 8
    if 'refuse' in guest_meta['first_name'].lower():
        guest_meta['name_data_quality'] = 9

    guest_meta['ssn_data_quality'] = 99
    guest_meta['veteran_status'] = 99
    guest_meta['hmis_version'] = datadict_menu_rev['hmis_version']
    return guest_meta


class db:
    """
    Database object for db operations.
    References:
    http://docs.sqlalchemy.org/en/latest/core/engines.html
    """
    def __init__(self, dbtype='sqlite+pysqlcipher',  password='', dbname=''):
        config = configparser.ConfigParser()
        config.read(fn_config)
        fn_datadict = config['DEFAULT']['fn_datadict']

        dbtype = dbtype.lower()
        self.db_engine = create_engine(
                '{0}://:{1}@/{2}?'
                'cipher=aes-256--cfb&kdf_iter=64000'.format(dbtype,
                                                            password,
                                                            dbname))
        Session = sessionmaker(bind=self.db_engine)
        self.session = Session()

        with open(fn_datadict) as f:
            self.datadict = json.load(f)

    def test_db_connection(self):
        try:
            self.db_engine.table_names()
            return True
        except DatabaseError:
            return False

    def create_db_tables(self):
        try:
            Base.metadata.create_all(self.db_engine)
            print("Tables created")
        except Exception as e:
            print("Error occurred during Table creation!")
            print(e)

    def add_guest(self, hmis_dict):
        self.session.add(Clients(**hmis_dict))
        self.session.commit()

    @staticmethod
    def nonzerocols(df):
        """
        Generic pandas operation to return column names
        for nonzero elements.
        """
        nonzero_cols = df.apply(lambda x: list(df.columns[x.values]), axis=1)
        return nonzero_cols.apply(lambda x: x[0] if len(x) == 1 else x)

    def query_allguestmeta(self):
        df_allguestmeta = pd.read_sql_table('clients', con=self.db_engine)
        df_allguestmeta.set_index('fr_id', inplace=True)
        df_allguestmeta_clean = (df_allguestmeta[['first_name', 'middle_name', 'last_name']]
                                 .join(pd.DataFrame({'Client Name': df_allguestmeta['first_name']
                                                     + ' '
                                                     + df_allguestmeta['middle_name']
                                                     + ' '
                                                     + df_allguestmeta['last_name'],
                                                     'Race': self.nonzerocols(df_allguestmeta[['am_ind_ak_native',
                                                                                               'asian',
                                                                                               'black_af_american',
                                                                                               'native_hi_other_pacific',
                                                                                               'white']].astype(bool)),
                                                     'Ethnicity': df_allguestmeta['ethnicity'].apply(lambda x: self.datadict['3.05.1']['data'][str(x)]),
                                                     'DOB': df_allguestmeta['dob'],
                                                     'Gender': df_allguestmeta['gender'].apply(lambda x: self.datadict['3.06.1']['data'][str(x)]),
                                                     })))
        df_allguestmeta_clean['Client Name'] = df_allguestmeta_clean['Client Name'].str.replace(' +', ' ', regex=True)
        return df_allguestmeta_clean

    def record_guest(self, dataframe):
        dataframe.to_sql('signin',
                         con=self.db_engine,
                         index=False,
                         if_exists='append')

    def record_startstop(self, dictionary):
        self.session.merge(SignSS(**dictionary))
        self.session.commit()

    def query_startstop(self):
        df_startstop = pd.read_sql_table('startstop',
                                         con=self.db_engine,
                                         parse_dates=['start_time',
                                                      'stop_time'])
        return df_startstop

    def query_mealsignin(self, start_date, stop_date):
        # Sqlite stores dates as strings, use sqlalchemy func to convert
        query_statement = (self.session.query(SignLog, Clients)
                           .filter(SignLog.fr_id == Clients.fr_id)
                           .filter(SignLog.time >= func.datetime(start_date))
                           .filter(SignLog.time <= func.datetime(stop_date))
                           .statement)
        df_signlog = pd.read_sql(query_statement, self.db_engine)
        df_meallog = pd.DataFrame({'Client Name': df_signlog['first_name']
                                   + ' '
                                   + df_signlog['middle_name']
                                   + ' '
                                   + df_signlog['last_name'],
                                   'Race': self.nonzerocols(df_signlog[['am_ind_ak_native',
                                                                        'asian',
                                                                        'black_af_american',
                                                                        'native_hi_other_pacific',
                                                                        'white']].astype(bool)),
                                   'Ethnicity': df_signlog['ethnicity'].apply(lambda x: self.datadict['3.05.1']['data'][str(x)]),
                                   'DOB': df_signlog['dob'],
                                   'Gender': df_signlog['gender'].apply(lambda x: self.datadict['3.06.1']['data'][str(x)]),
                                   'First Time': df_signlog['first_time'].apply(lambda x: {0: 'No', 1: 'Yes'}[x])})
        df_meallog['Client Name'] = df_meallog['Client Name'].str.replace(' +',' ', regex=True)
        return df_meallog

    def print_all_data(self, table='', query=''):
        query = query if query != '' else "SELECT * FROM '{}';".format(table)
        with self.db_engine.connect() as connection:
            try:
                result = connection.execute(query)
            except Exception as e:
                print(e)
            else:
                for row in result:
                    print(row)
                result.close()
        print("\n")
