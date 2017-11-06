import pandas as pd
import numpy as np

#transltates from iso 3166-1 alpha-2 to iso 3166-1 alpha-3
class Geo:
	def __init__(self):
		#http://lite.ip2location.com/database/ip-country
		self.geodb = pd.read_csv('dbs/IP2LOCATION-LITE-DB1.CSV', names=['ip_from', 'ip_to', 'code', 'country'], dtype={'ip_from': int, 'ip_to': int, 'code': str, 'country': str})
		self.codes = pd.read_csv('dbs/country_codes_bis.csv', sep=',', names=['country', 'code', 'long_code'], index_col='code', dtype=str)
		self.geodb['code'] = self.geodb['code'].apply(self._get_long_code)

	def get_code_and_country_from_ip(self, int_ip):
		#return self.geodb.query('ip_from <= @int_ip and ip_to >= @int_ip')[['code', 'country']].values.tolist()[0]
		geo = self.geodb
		return geo[(geo['ip_from'] <= int_ip) & (geo['ip_to'] >= int_ip)][['code', 'country']].values.tolist()[0]

	def _get_long_code(self, code):
		code = str(code)
		if code in self.codes.index:
			long_code = self.codes.at[code, 'long_code']
			return long_code[0] if isinstance(long_code, np.ndarray) else long_code
		return '-' if code == '-' else False
	
	def fill_blank_dataframe(self, grouped, agg_field, field):
                #this function fills an empty dataframe with the data given
                #this allows us to have a dataframe with zeros in the countries
                #without requests
                blank = self.codes[['country', 'long_code']].copy()
                blank.columns = ['country', 'code']
                blank.set_index('code', inplace=True)
                blank[field] = grouped[field]
                blank[field] = blank[field].fillna(0)
                blank[agg_field] = grouped[agg_field]
                blank[agg_field] = blank[agg_field].fillna('')
                blank.reset_index(inplace=True)
                blank = blank.sort_values(field, ascending=False)
                return blank