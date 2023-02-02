"""

Cloudworks Scrayping Tool

"""

import clowdworks_scray as cs
from time import sleep

with open('clowdworks_url', 'r', encoding='utf-8_sig') as cf:
	cloudworks_urls = cf.readlines()
while True:
	print('processing start')
	for cloudworks_url in cloudworks_urls:
		cs.scray(cloudworks_url)
	print('End of process Atmospheric')
	sleep(10)

