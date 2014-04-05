from datetime import datetime
from dateutil.relativedelta import relativedelta
from email.utils import parseaddr
import pandas
from pandas import Index, Series
import numpy as np
import csv
import json
import argparse

class OrderValidator():

    bad_states = "NJ CT PA MA IL ID OR".split(' ')

    def __init__(self, args=None):
        self.args = args
        
    def read_csv(self, file_name=None):
        if not file_name:
            file_name = self.args.input_file_name

        birthday_index = 5
        with open(file_name, 'r') as f:
            reader = csv.reader(f, delimiter='|')
            for i, row in enumerate(reader):
                if i == 0:
                    for j, title in enumerate(row):
                        if title == 'birthday':
                            birthday_index = j
                    break

        self.orig_df = pandas.read_csv(file_name, sep='|', parse_dates=[birthday_index])
        self.df = self.orig_df.copy()

    def clean_data(self):
        for column_name in self.df:
            self.df = self.df[self.df[column_name].notnull()]
        self.df['zipcode'] = self.df['zipcode'].astype(int)
        self.df['id'] = self.df['id'].astype(int)

    def filter_by_rules(self):
        df = self.df
        
        df = self.apply_rule_6(df)
        df = self.apply_rule_1(df)
        df = self.apply_rule_2(df)
        df = self.apply_rule_3(df)
        df = self.apply_rule_4(df)
        df = self.apply_rule_5(df)

        self.df = df

    def apply_rule_1(self, df):
        df = df[~df.state.isin(self.bad_states)]
        return df

    def apply_rule_2(self, df):
        df = df[df.zipcode.apply(lambda z: True if z and len(str(z)) in (5,9) else False)]
        return df

    def apply_rule_3(self, df):
        _21_years_ago = datetime.now() - relativedelta(years=21)
        df = df[Series(_21_years_ago - df.birthday) >= 0]
        return df

    def apply_rule_4(self, df):
        df = df[df.email.apply(lambda e: True if parseaddr(e)[1] else False)]
        return df

    def apply_rule_5(self, df):
        df = df[df.zipcode.apply(lambda z: True if sum([int(x) for x in str(z)]) <= 20 else False)]    
        return df

    def apply_rule_6(self, df):
        safe_list = []
        prev_i = None
        prev_zipcode = None
        prev_state = None
        for i in df.index.tolist():
            if df.ix[i]['state'] == prev_state and df.ix[i]['zipcode'] == prev_zipcode:
                safe_list += [prev_i]

            prev_state = df.ix[i]['state']
            prev_zipcode = df.ix[i]['zipcode']
            prev_i = i

        self.safe_index = Index(safe_list)

        return df

    def prepare_output_dfs(self, detailed=False):
        valid_df = self.orig_df.reindex(self.safe_index | self.df.index)
        invalid_df = self.orig_df.drop(valid_df.index)
        invalid_df = invalid_df[invalid_df.name.notnull()]
        invalid_df['name'] = invalid_df['name'].apply(lambda n: n[::-1])
        
        if detailed:
            self.valid_df = valid_df
            self.invalid_df = invalid_df
        else:
            self.valid_df = valid_df[['id', 'name']]
            self.invalid_df = invalid_df[['id', 'name']]

    def output_as_csv(self):
        valid_df = self.valid_df
        invalid_df = self.invalid_df

        valid_df.to_csv('valid.csv', index=False, float_format='%.0f')
        invalid_df.to_csv('invalid.csv', index=False, float_format='%.0f')

        print "Output: valid.csv invalid.csv"

    def output_as_json(self):
        valid_df = self.valid_df
        invalid_df = self.invalid_df

        valid_df.to_json('valid.json')
        invalid_df.to_json('invalid.json')
        
        print "Output: valid.json, invalid.json"


if __name__ == "__main__":

    # Process arguments
    parser = argparse.ArgumentParser(description='Validate Orders')
    parser.add_argument("-i", dest="input_file_name", required=True, help="Input file (csv)", metavar="FILE")
    parser.add_argument("--json", required=False, help="JSON option", action="store_true")
    parser.add_argument("--detailed", required=False, help="Detailed output option", action="store_true")
    args = parser.parse_args()

    # Read data, filter
    order_validator = OrderValidator(args=args)
    order_validator.read_csv()
    order_validator.clean_data()
    order_validator.filter_by_rules()
    order_validator.prepare_output_dfs(detailed=args.detailed)

    # Generate output
    if args.json:
        order_validator.output_as_json()
    else:
        order_validator.output_as_csv()
