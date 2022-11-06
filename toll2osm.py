#!/usr/bin/env python3
# -*- coding: utf8

# toll2osm
# Converts toll booths/gantries from NVDB json api to osm format for import/update
# Usage: python toll2osm.py [nvdb|autopass]

# Alternative api from Autopass: https://www.autopass.no/System/alleanleggjson
# (Currently not working)


import html
import json
import sys
import urllib.request
from datetime import datetime


version = "1.1.0"

header = {
	"X-Client": "NKAmapper/toll2osm",
	"X-Kontaktperson": "nkamapper@gmail.com",
	"Accept": "application/vnd.vegvesen.nvdb-v3-rev1+json"
}
	

# Output message

def message (line):

	sys.stdout.write (line)
	sys.stdout.flush()


# Produce a tag for OSM file

def make_osm_line (key, value):

	if value:
		escaped_value = html.escape(value).strip()
		out_file.write ('    <tag k="%s" v="%s" />\n' % (key, escaped_value))


# Create amount string

def amount (value):

	if value == abs(value):
		return "%i" % int(value)
	else:
		return "%.2f" % value


# Generate toll stations from NVDB

def get_nvdb():

	global toll_count

	# Loop all toll stations and produce OSM file, page by page

	node_id = -1000
	returned = 1

	url = "https://nvdbapiles-v3.atlas.vegvesen.no/vegobjekter/45?inkluder=metadata,egenskaper,lokasjon,geometri&alle_versjoner=false&srid=wgs84"

	while returned > 0:

		# Load toll stations from NVDB api (next page)

		request = urllib.request.Request(url, headers=header)
		file = urllib.request.urlopen(request)
		toll_data = json.load(file)
		file.close()

		for toll in toll_data['objekter']:

			node_id -= 1
			toll_count += 1

			info = {}
			for toll_info in toll['egenskaper']:
				if "verdi" in toll_info:
					info[ toll_info['navn'] ] = toll_info['verdi']

			wkt = toll['lokasjon']['geometri']['wkt'].replace("POINT Z (", "").replace("POINT Z(", "").replace("POINT (", "").replace(")", "")
			coordinate = wkt.split()

			out_file.write ('  <node id="%i" lat="%s" lon="%s">\n' % (node_id, coordinate[0], coordinate[1]))

			# Tagging

			if "Bomstasjonstype" in info and "automatisk" in info['Bomstasjonstype']:
				make_osm_line ("highway", "toll_gantry")
			else:
				make_osm_line ("barrier", "toll_booth")

			make_osm_line ("ref:toll", str(toll['id']))

			if "Navn bomstasjon" in info:
				name = info['Navn bomstasjon'].replace("  ", " ").strip()
				if name == name.upper():
					name = name.title()
				if name[0:2].lower() == "fv":
					name = name.replace("FV", "Fv").replace("fv", "Fv").replace("Fv.", "Fv").replace("Fv ", "Fv")
				if name[0:2].lower() == "rv":
					name = name.replace("RV", "Rv").replace("rv", "Rv").replace("Rv.", "Rv").replace("Rv ", "Rv")
				make_osm_line ("name", name)

			if "Navn bompengeanlegg (fra CS)" in info:
				operator = info['Navn bompengeanlegg (fra CS)'].replace("  ", " ").strip()
				if operator == operator.upper():
					operator = operator.title().replace(" As", " AS")
				make_osm_line ("operator", operator)

#			if "Link til bomstasjon" in info:
#				make_osm_line ("contact:website", "http://" + info['Link til bomstasjon'])  # Not https

			if "Etableringsår" in info:
				make_osm_line ("start_date", str(info['Etableringsår']))

			if "Vedtatt til år" in info and info['Vedtatt til år'] >= year_now:
				make_osm_line ("end_date", str(info['Vedtatt til år']))

			# Fee tagging

			duration = ""
			if "Timesregel" in info and info['Timesregel'] == "Standard timesregel":
				if "Timesregel, varighet" in info:
					if info['Timesregel, varighet'] == 60:
						duration = "/hour"
					else:
						duration = "/%i minutes" % info['Timesregel, varighet']

				else:
					duration = "/hour"

			if "Takst liten bil" in info:
				make_osm_line ("charge:motorcar", "%s NOK%s" % (amount(info['Takst liten bil']), duration))

				if "Takst stor bil" in info and info['Takst stor bil'] != info['Takst liten bil']:
					make_osm_line ("charge:hgv", "%s NOK%s" % (amount(info['Takst stor bil']), duration))

			if "Gratis gjennomkjøring ved HC-brikke" in info and info['Gratis gjennomkjøring ved HC-brikke'] == "Ja":
				make_osm_line ("toll:disabled", "no")

			if "Tidsdifferensiert takst" in info and info['Tidsdifferensiert takst'] == "Ja" and "Rushtidstakst liten bil" in info \
					and "Rushtid morgen, fra" in info:
				times = "Mo-Fr %s-%s, %s-%s; PH off" % \
						(info['Rushtid morgen, fra'], \
						info['Rushtid morgen, til'].replace("08:29", "08:30").replace("08:59", "09:00"), \
						info['Rushtid ettermiddag, fra'], \
						info['Rushtid ettermiddag, til'].replace("16:29", "16:30").replace("16:59", "17:00"))

				make_osm_line ("charge:motorcar:conditional", "%s NOK%s @ (%s)" % (amount(info['Rushtidstakst liten bil']), duration, times))

				if info['Rushtidstakst stor bil'] != info['Rushtidstakst liten bil']:
					make_osm_line ("charge:hgv:conditional", "%s NOK%s @ (%s)" % (amount(info['Rushtidstakst stor bil']), duration, times))

			# Extra information

			if "Innkrevningsretning" in info:
				make_osm_line ("RETNING", info['Innkrevningsretning'])

			if "sist_modifisert" in toll['metadata']:
				make_osm_line ("MODIFISERT", toll['metadata']['sist_modifisert'][0:10])
			else:
				make_osm_line ("MODIFISERT", toll['metadata']['startdato'][0:10])

			make_osm_line ("OPPRETTET", toll['metadata']['startdato'][0:10])

			out_file.write ('  </node>\n')

		# Prepare for next page of data

		returned = toll_data['metadata']['returnert']
		url = toll_data['metadata']['neste']['href']


# Generate toll stations from Autopass (currently not working)

def get_autopass():

	global toll_count

	url = "https://www.autopass.no/System/alleanleggjson"
	request = urllib.request.Request(url)
	file = urllib.request.urlopen(request)
	toll_data = json.load(file)
	file.close()
	node_id = -1000

	for toll in toll_data['bomstasjoner']['bomstasjon']:

		toll_count += 1
		node_id -= 1

		latitude, longitude = toll['lat'], toll['lon']
		if not latitude:
			latitude = 0.0
		if not longitude:
			longitude = 0.0

		out_file.write ('  <node id="%i" lat="%s" lon="%s">\n' % (node_id, latitude, longitude))
		make_osm_line ("highway", "toll_gantry")
		make_osm_line ("ref:autopass", "%i-%i" % (toll['bomanleggid'], toll['bomstasjonsid']))
		make_osm_line ("name", toll['bomstasjonsnavn'])
		out_file.write ('  </node>\n')


# Main program

if __name__ == '__main__':

	year_now = datetime.now().year
	
	# Produce OSM file header

	filename = "bomstasjoner.osm"
	out_file = open(filename, "w")

	out_file.write ('<?xml version="1.0" encoding="UTF-8"?>\n')
	out_file.write ('<osm version="0.6" generator="toll2osm v%s" upload="false">\n' % version)

	toll_count = 0

	if len(sys.argv) > 1 and sys.argv[1].lower() == "autopass":
		get_autopass()

	else:
		get_nvdb()


	# Produce OSM file footer

	out_file.write ('</osm>\n')
	out_file.close()

	message ("%s toll stations saved in file '%s'\n" % (toll_count, filename))
