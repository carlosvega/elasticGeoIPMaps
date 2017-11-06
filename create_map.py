# -*- coding: utf-8 -*-
from elasticsearch import Elasticsearch, helpers
from elasticsearch_dsl import Search, Q, A, Mapping, Index, String
import json, time, logging, sys, inspect, argparse, functools, copy
from argparse import RawTextHelpFormatter
from utils.netutils import *
from utils.geoutils import * 
import pandas as pd
import numpy as np
import logging

#change the elasticsearch log level
logging.getLogger('elasticsearch').setLevel(logging.WARNING)
logging.basicConfig(level = logging.INFO, format = '[%(asctime)s %(levelname)s]\t%(message)s')

def parse_args():
	parser = argparse.ArgumentParser(description='Creates map from data in Elasticsearch.', formatter_class=RawTextHelpFormatter)
	parser.add_argument('--index', dest='index', default='ymetric-*-top_ips_span60.txt', required=False, help='Index pattern')
	parser.add_argument('--file', dest='filename', default=False, required=False, help="If you want to load data from file, use this option and provide the date range in seconds.\n\n\n~~ TIME FILTER OPTIONS ~~\n\n")
	
	
	parser.add_argument('--to', dest='lt', required=False, default=None, help='Indicates end of date interval.')
	parser.add_argument('--from', dest='gt', required=False, default=None, help="Indicates the beginning of date interval.")
	parser.add_argument('--tz', dest='tz', required=False, default='Europe/Madrid', help="Indicates the tz of the dates in both the file and the provided filters (--to and --from).\n\n\n~~ DATA FORMAT OPTIONS ~~\n\n")

	parser.add_argument('--agg-field', dest='agg_field', required=False, default="ip_cliente", help='Indicates aggregate metric to use. This is, the IP field in the elasticsearch index.')
	parser.add_argument('--date-field', dest='datefield', required=False, default='fecha', help='Field name for the date.')
	parser.add_argument('--value-field', dest='field', required=False, default="num_peticiones_en_intervalo", help='Indicates metric field to use. For example, the number of visits from that IP.')
	parser.add_argument('--separator', dest='separator', required=False, default=";", help='Indicates the field delimiter if a file is used.\n\n\n~~ ELASTIC QUERY OPTIONS ~~\n\n')
	
	
	parser.add_argument('--queries', dest='queries', nargs='+', metavar='N', required=False, default=[], help='List of strings in the form "field:value field2:value that will be joined with the operator AND or OR depending on the flag --or. Default: AND"')
	parser.add_argument('--or', dest='or_', default=False, action='store_true', help='Join queries with OR operation instead of AND.\n\n\n~~ MAP STYLE OPTIONS ~~\n\n')
	
	parser.add_argument('--title', dest='title', default='Web visits', action='store_true', help='Title of the map.')
	args = parser.parse_args()

	if args.filename != False:
		try:
			args.gt = pd.Timestamp(int(args.gt), unit='s', tz=args.tz) if args.gt is not None else pd.Timestamp.min
			args.lt = pd.Timestamp(int(args.lt), unit='s', tz=args.tz) if args.lt is not None else pd.Timestamp.max
		except ValueError:
			logging.error('Please, if you are loading data from file, provide a time range in seconds instead of relative times.')
			sys.exit(-1)
	else:
		#prepare queries
		#time span query for elasticsearch
		time_span = {
		 args.datefield: {
		  'gt': args.gt,
		  'lt': args.lt
		 }
		}

		#remove Nones
		for k in time_span[args.datefield].keys():
			if time_span[args.datefield][k] is None:
				del time_span[args.datefield][k] 

		q_ts = Q('range', **time_span)

		#create an array of queries and join them with AND or OR
		queries = []
		join_q = None
		for q in args.queries:
				q=q.split(':')
				q={q[0]:q[1]}
				q = Q('match', **q)
				queries.append(q)
		if len(queries) > 0:
			join_q = queries[0]
			for q in queries[1:]:
				if args.or_:
					join_q = join_q | q
				else:
					join_q = join_q & q
			queries = [join_q]	
		queries.append(q_ts)	
		args.queries = queries

	return args
	
#Get data from Elasticsearch
def get_data_from_elastic(index, field, agg_field, gt='now-2d', lt='now', datefield='fecha', queries=[], size=100000):
	client = Elasticsearch(timeout=120)
	s = Search(using=client).index(index).fields([datefield, field])
	#time span query
	time_span = {
	 datefield: {
	  'gt': gt,
	  'lt': lt
	 }
	}
	q_ts = Q('range', **time_span)
	queries.append(q_ts)
	for q in queries:
		s = s.query(q)
	#aggregation per IP
	agg = A('terms', field=agg_field, size=size)
	s.aggs.bucket('agg', agg).metric(field, 'sum', field=field)
	response = s.execute()
	rows = []
	for ip in response.aggregations['agg'].buckets:
		rows.append([ip.key_as_string, int(ip.key), int(ip[field].value)])
	df = pd.DataFrame(rows, columns=[agg_field, 'intIP', field])
	return df

#group ips
def group_ips(df, field):
	grouped = df.groupby(['country', 'code']).sum().reset_index().set_index('code')
	grouped['IPs'] = ''
	for group in grouped.itertuples():
		code = group[0]
		ctry  = group[1]
		top_ips = df[df['country'] == ctry].groupby('intIP').sum().sort_values(field, ascending=False).head(10).index.tolist()
		top_ips = [int2ip(ip) for ip in top_ips]
		top_ips = '<br>'.join(top_ips)
		grouped.set_value(code, 'IPs', top_ips)
	return grouped

#create the map
def plot_map(info, agg_field, field, title='Web Requests', filename='geoip_map.html'):
	import plotly
	info['country'] = info['country'].apply(lambda x: x.capitalize())	
	data = [ dict(
			type = 'choropleth',
			locations = info['code'],
			z = info[field],
			text = info['country'] + '<br>' + info[agg_field],
			colorscale = [[0,"rgb(255, 68, 68)"],[0.5,"rgb(255, 180, 68)"], [0.93, "rgb(161, 255, 153)"],[0.999,"rgb(63, 69, 255)"], [1,"rgb(255, 255, 255)"]],
			autocolorscale = False,
			reversescale = True,
		hoverinfo = 'location+text+z',
			marker = dict(
				line = dict (
					color = 'rgb(180,180,180)',
					width = 0.5
				) ),
			colorbar = dict(
				title = field),
	) ]
	layout = dict(
		separators = ',.',
		title = title + '<br> <a href="geoip_converted.csv"> Download raw CSV </a>',
		geo = dict(
			showframe = True,
			showcoastlines = True,
			scope='world',
			projection=dict( type='equirectangular' )
		)
	)
	fig = dict( data=data, layout=layout )
	plotly.offline.plot( fig, validate=True, filename=filename )
	
#example
#change data from an specific internal subnet to their proper country
def correct_countries(row):
		#check if ip in network
		if in_net(row['intIP'], "11.98.0.0/16"):
				row['country'] = 'spain'
				row['code'] = 'ES'
		return row

#transform the rows
def shape_rows(row, g):
	code, country = g.get_code_and_country_from_ip(row['intIP'])
	country = country if country != '-' else 'spain'
	code = code if code != '-' else 'ES'
	row['country'] = country
	row['code'] = code
	#row = correct_countries(row)
	return row

#remove internal ips
def is_internal(intIP):
	subnets = ["11.98.0.0/16", "192.168.0.0/16", "193.168.0.0/16", "10.98.0.0/16"]
	for net in subnets:
		if in_net(intIP, net):
			return True
	return False

#execution parameters 
args = parse_args()
logging.info(args)

logging.info('Creating map from {} to {}'.format(args.gt, args.lt))
#load codes info
gg = Geo()
logging.info('GeoIP and Country codes information loaded')


if not args.filename:
	#load data from elastic
	df = get_data_from_elastic(args.index, args.field, args.agg_field, gt=args.gt, lt=args.lt, queries=args.queries, datefield=args.datefield)
	logging.info('Information retrieved from elasticsearch')
else:
	try:
		#load data from file
		df = pd.read_csv(args.filename, sep=args.separator, dtype={args.field: float, args.agg_field: int, args.datefield: float}, usecols=[args.field, args.agg_field, args.datefield])
		#convert float to date
		df[args.datefield] = df[args.datefield].apply(lambda x: pd.Timestamp(x, unit='s', tz=args.tz))
		#set index by date
		df.set_index(args.datefield, inplace=True)
		#filter file 
		mask = (args.gt < df.index) & (df.index < args.lt)
		df = df[mask]
		#reset index
		df.reset_index(inplace=True)
		df = df[[args.field, args.agg_field, args.datefield]]
		df.columns = [args.field, 'intIP', args.datefield]
		#change column name
	except Exception as e:
		logging.error('Please, check your file format. Field separator, header, provided column names, etc.')
		logging.error(e)
		raise
		sys.exit(-1)

#meter informacion de pais y codigo
df = df[~df['intIP'].apply(is_internal)]
logging.info('Removed internal IPs')
shape_rows_partial = functools.partial(shape_rows, g=gg)
df = df.apply(shape_rows_partial, axis=1)
df = df[df['code'] != False]
logging.info('Rows shaped')

grouped = group_ips(df, args.field) #agrupar por pais y meter top de ips
logging.info('DataFrame grouped')

#FILL DATAFRAME WITH ALL THE COUNTRIES 
blank = gg.fill_blank_dataframe(grouped, 'IPs', args.field)
logging.info('Plotting map to geoip_map.html ...')
plot_map(blank, 'IPs', args.field, title=args.title)

logging.info('Map finished!')
df.to_csv('geoip_converted.csv', sep=';', columns=[args.agg_field, 'country', 'code', args.field], index=False, encoding='utf-8')
logging.info('DataFrame saved to CSV file correos.csv')









