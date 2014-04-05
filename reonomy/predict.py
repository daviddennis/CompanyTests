import pandas
from pandas import Series
import numpy as np
from datetime import datetime
import argparse
import locale

class PricePredictor():
    
    def __init__(self):
        parser = argparse.ArgumentParser(description='Predict Building Price')
        parser.add_argument("-i", dest="input_file", required=True, help="Input file (csv)", metavar="FILE")
        parser.add_argument("-a", dest="address", required=True, help="Address to Predict")

        self.args = parser.parse_args()

    def prepare_data(self):
        # Read CSV data into Pandas DataFrame
        df = pandas.read_csv(self.args.input_file, parse_dates=[3])
        
        # Get earliest date in dataset
        df = df.set_index('sale_date')
        df.sort(inplace=True)
        self.orig_date = np.datetime64(str(df.ix[0].name))

        sub_df = df

        # Calculate more convenient column for number of days passed, re-index and sort
        num_days_array = sub_df.index.values - np.datetime64(str(self.orig_date))
        sub_df['num_days'] = Series(num_days_array, index=sub_df.index).apply(lambda x: x / np.timedelta64(1,'D'))
        sub_df = sub_df.set_index('num_days')
        sub_df.sort_index(inplace=True)
        
        self.df = sub_df

    def get_address_filtered_df(self):
        sub_df = self.df

        # Filter by address given
        sub_df = sub_df[sub_df['address'] == self.args.address]
        return sub_df

    def get_predicted_price(self):
        sub_df = self.get_address_filtered_df()

        # Perform ordinary least squares regression on # days passed and sale price
        x = sub_df.index.values
        y = sub_df.sale_price.values
        A = np.vstack([x, np.ones(len(x))]).T
        m, b = np.linalg.lstsq(A, y)[0]
        current_num_days = (datetime.now() - pandas.to_datetime(self.orig_date)).days

        # Calculate and return predicted price for this address
        predicted_price = m*current_num_days + b
        return predicted_price

    def get_sparse_prediction(self, address_filtered_df, zip_code):
        sub_df = self.df
        sub_df = sub_df[sub_df['zipcode'] == zip_code]

        # Calculate price per square foot for this area
        sub_df['price_per_sqft'] = sub_df.sale_price / sub_df.square_footage

        # Get time weight column
        num_days_sum = sub_df.index.values.sum()
        sub_df['normalized_num_days'] = Series(sub_df.index.values, index=sub_df.index).apply(lambda x: x/ num_days_sum)
        
        # Calculate time-weighted price per square foot
        price_per_sqft_prediction = (sub_df.price_per_sqft * sub_df.normalized_num_days).sum()

        square_footage = address_filtered_df.square_footage.ix[0]
        sale_price_prediction = price_per_sqft_prediction * square_footage

        return sale_price_prediction


if __name__ == "__main__":

    price_predictor = PricePredictor()
    price_predictor.prepare_data()

    # Calculate predicted price
    sub_df = price_predictor.get_address_filtered_df()
    if len(sub_df) < 2:
        predicted_price = price_predictor.get_sparse_prediction(sub_df, sub_df['zipcode'].ix[0])
    else:
        predicted_price = price_predictor.get_predicted_price()

    locale.setlocale( locale.LC_ALL, '' )
    print locale.currency(predicted_price, grouping=True)

