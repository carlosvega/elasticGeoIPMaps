# elasticGeoIPMaps

<iframe src="https://carlosvega.github.io/elasticGeoIPMaps/geoip_map.html" width="640" height="480" style="display:block; margin: 0 auto;" frameBorder="0">&nbsp;</iframe>

This tool creates a choropleth map from data stored in an elasticsearch database or from data stored in a CSV file.

Is a draft tool so, it lacks some options about the elasticsearch connection, such as the host, port or SSL stuff. It assumes elasticsearch is running in localhost and port 9200. But the code can be easily changed [looking at this example](https://elasticsearch-py.readthedocs.io/en/master/#ssl-and-authentication). I will try to add these options in the future if I have time, but, at the moment, I don't require them for myself. Feel free to fork it or propose new changes.

## Pre-requirements

```
python 2.x, pip
```

## Set-up instructions
```
git clone https://github.com/carlosvega/elasticGeoIPMaps.git elasticGeoIPMaps
cd elasticGeoIPMaps
pip install virtualenv
virtualenv .env
source .env/bin/activate
pip install -r requirements.txt
```

## Run an example
```
python create_map.py --file examples/example.csv --from $(date -d "2017/11/01 12:30" +%s) --value-field visits --agg-field client_ip --date-field date --dir test
```

This will create an HTML map and a CSV file:
```
test/geoip_converted.csv
test/geoip_map.html
```

## Some comments

Developing this tool in JavaScript in order to run much of the process in the client side is no challenge at all. Is quite straightforward if you make use of [plotly.js](https://plot.ly/javascript/). I currently have a JavaScript version (a bit unclean). It just needs to load the CSV file with the IP-country relationship table, retrieve the data from elasticsearch trhough elastic REST API and make a few data conversions in order to plot it. Is of course much faster than doing it on python. I will update this page if I decide to make the JavaScript version available for the public.
