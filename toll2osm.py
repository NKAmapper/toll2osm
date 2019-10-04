#!/usr/bin/env python
# -*- coding: utf8

# toll2osm
# Converts toll booths/gantries from NVDB json api to osm format for import/update
# Usage: python toll2osm.py


import cgi
import json
import sys
import urllib2
from datetime import datetime


version = "0.4.0"

header = {"User-Agent": "osm-no/toll2osm"}

	

# Output message

def message (line):

	sys.stdout.write (line)
	sys.stdout.flush()


# Produce a tag for OSM file

def make_osm_line (key, value):

    if value:
		encoded_value = cgi.escape(value.encode('utf-8'),True).strip()
		file.write ('    <tag k="%s" v="%s" />\n' % (key, encoded_value))


# Create amount string

def amount (value):

	if value == abs(value):
		return "%i" % int(value)
	else:
		return "%.2f" % value


# Main program

if __name__ == '__main__':

	year_now = datetime.now().year

	# Load county id's and names from Kartverket api

	link = "https://ws.geonorge.no/kommuneinfo/v1/fylker"
	request = urllib2.Request(link, headers=header)
	file = urllib2.urlopen(request)
	county_data = json.load(file)
	file.close()

	counties = {}
	for county in county_data:
		counties[ int(county['fylkesnummer']) ] = county['fylkesnavn'].strip()

	# Load toll stations from NVDB api

	link = "https://www.vegvesen.no/nvdb/api/v2/vegobjekter/45?segmentering=true&inkluder=lokasjon,metadata,egenskaper&srid=wgs84"
	request = urllib2.Request(link, headers=header)
	file = urllib2.urlopen(request)
	toll_data = json.load(file)
	file.close()

	message ("%s toll stations\n" % len(toll_data['objekter']))

	# Produce OSM file header

	filename = "bomstasjoner.osm"
	file = open(filename, "w")

	file.write ('<?xml version="1.0" encoding="UTF-8"?>\n')
	file.write ('<osm version="0.6" generator="toll2osm v%s" upload="false">\n' % version)

	node_id = -1000

	# Loop all toll stations and produce OSM file

	for toll in toll_data['objekter']:

		node_id -= 1

		info = {}
		for toll_info in toll['egenskaper']:
			info[ toll_info['navn'] ] = toll_info['verdi']

		wkt = toll['lokasjon']['geometri']['wkt'].replace("POINT Z (", "").replace("POINT (", "").replace(")", "")
		coordinate = wkt.split()

		file.write ('  <node id="%i" lat="%s" lon="%s">\n' % (node_id, coordinate[0], coordinate[1]))

		# Tagging

		if "Bomstasjonstype" in info and "automatisk" in info['Bomstasjonstype']:
			make_osm_line ("highway", "toll_gantry")
		else:
			make_osm_line ("barrier", "toll_booth")

		make_osm_line ("ref:toll", str(toll['id']))

		if "Navn bomstasjon" in info:
			make_osm_line ("name", info['Navn bomstasjon'])

		if "Navn bompengeanlegg (fra CS)" in info:
			make_osm_line ("operator", info['Navn bompengeanlegg (fra CS)'])

		if "Link til bomstasjon" in info:
			make_osm_line ("contact:website", "https://" + info['Link til bomstasjon'])

		if u"Etableringsår" in info:
			make_osm_line ("start_date", str(info[u'Etableringsår']))

		if u"Vedtatt til år" in info and info[u'Vedtatt til år'] >= year_now:
			make_osm_line ("end_date", str(info[u'Vedtatt til år']))

		# Fee tagging

		if "Takst liten bil" in info:
			make_osm_line ("fee:motorcar", amount(info['Takst liten bil']))

			if "Takst stor bil" in info and info['Takst stor bil'] != info['Takst liten bil']:
				make_osm_line ("fee:hgv", amount(info['Takst stor bil']))

		else:
			make_osm_line ("fee:motorcar", "yes")

		if u"Gratis gjennomkjøring ved HC-brikke" in info and info[u'Gratis gjennomkjøring ved HC-brikke'] == "Ja":
			make_osm_line ("fee:disabled", "no")

		if "Tidsdifferensiert takst" in info and info['Tidsdifferensiert takst'] == "Ja" and "Rushtidstakst liten bil" in info:
			times = "Mo-Fr %s-%s, %s-%s; PH off" % \
					(info['Rushtid morgen, fra'], \
					info['Rushtid morgen, til'].replace("08:29", "08:30").replace("08:59", "09:00"), \
					info['Rushtid ettermiddag, fra'], \
					info['Rushtid ettermiddag, til'].replace("16:29", "16:30").replace("16:59", "17:00"))

			make_osm_line ("fee:motorcar:conditional", "%s @ (%s)" % (amount(info['Rushtidstakst liten bil']), times))

			if info['Rushtidstakst stor bil'] != info['Rushtidstakst liten bil']:
				make_osm_line ("fee:hgv:conditional", "%s @ (%s)" % (amount(info['Rushtidstakst stor bil']), times))			

		if "Timesregel" in info and info['Timesregel'] == "Standard timesregel":
			if "Timesregel, varighet" in info:
				make_osm_line ("fee:duration", "{:02d}:{:02d}".format( *divmod(info['Timesregel, varighet'], 60)) )
			else:
				make_osm_line ("fee:duration", "01:00")

		# Extra information

		if "Innkrevningsretning" in info:
			make_osm_line ("RETNING", info['Innkrevningsretning'])

		make_osm_line ("FYLKE", counties[ toll['lokasjon']['fylker'][0] ])

		if "sist_modifisert" in toll['metadata']:
			make_osm_line ("MODIFISERT", toll['metadata']['sist_modifisert'][0:10])
		else:
			make_osm_line ("MODIFISERT", toll['metadata']['startdato'][0:10])

		make_osm_line ("OPPRETTET", toll['metadata']['startdato'][0:10])

		file.write ('  </node>\n')

	# Produce OSM file footer

	file.write ('</osm>\n')
	file.close()

	message ("Saved in file '%s'\n" % filename)

