import yaml
import sys
import os
import time
from tabulate import tabulate
import logging
import smtplib
from datetime import datetime

class global_config(object):
	"""
		This class parses the configuration file which defaults to config/config.yaml and the config/connection.yaml if not specified.
		The class variables used by the other libraries are retrieved from the yaml configuration file. 
		A separate connection file defaults to config/connection.yaml if no file is specified.
		The constructor checks if the configuration file is present and emits an error message followed by
		the sys.exit() command if the files are missing. 
		The class sets the log output file name using the start date and  from the parameter command.  If the log destination is stdout then the logfile is ignored
		
	
	"""
	def __init__(self, connection_file, load_config=False):
		"""
			Class  constructor.
		"""
		if connection_file:
			self.connection_file = connection_file
			if load_config:
				self.load_config()
		else:
			print("**FATAL - invalid connection file specified **\Expected filename got %s." % (self.connection_file))
			sys.exit(1)
	
	def set_copy_max_memory(self):
		copy_max_memory = str(self.copy_max_memory )[:-1]
		copy_scale=str(self.copy_max_memory )[-1]
		try:
			int(copy_scale)
			copy_max_memory = self.copy_max_memory 
		except:
			if copy_scale =='k':
				copy_max_memory = str(int(copy_max_memory)*1024)
			elif copy_scale =='M':
				copy_max_memory = str(int(copy_max_memory)*1024*1024)
			elif copy_scale =='G':
				copy_max_memory = str(int(copy_max_memory)*1024*1024*1024)
			else:
				print("**FATAL - invalid suffix in parameter copy_max_memory  (accepted values are (k)ilobytes, (M)egabytes, (G)igabytes.")
				sys.exit()
		self.copy_max_memory = copy_max_memory
	
	
	def set_conn_vars(self, conndic):
		for key in conndic:
			try:
				setattr(self, key, conndic[key])
				print (key)
			except KeyError as key_missing:
				print('Using global value for key %s ' % (key_missing, ))
		self.set_copy_max_memory()	
		
		
	
	def load_connection(self):
		""" 
		"""
		
		if not os.path.isfile(self.connection_file):
			print("**FATAL - connection file missing **\ncopy config/connection-example.yaml to %s and set your connection settings." % (self.connection_file))
			sys.exit()
		
		connectfile = open(self.connection_file, 'r')
		self.connection = yaml.load(connectfile.read())
		connectfile.close()
		conndic = self.connection
		for key in conndic:
			setattr(self, key, conndic[key])
		self.set_copy_max_memory()	
		self.log_file =  "%s/%s.log" % (self.log_dir, key)
		
		
		

class replica_engine(object):
	def __init__(self, conn_file):
		self.global_config = global_config(conn_file)
	
	def create_service_schema(self):
		print("ok")
	
	def list_connections(self):
		self.global_config.load_connection()
		tab_headers=["Connection key", "Source host", "Destination host", "Replica type"]
		tab_body=[]
		self.conn_list=self.global_config.connection["connections"]
		for connkey in self.conn_list:
			conndic = self.conn_list[connkey]
			tab_row=[connkey, conndic["src_conn"]["host"], conndic["dest_conn"]["host"] , conndic["src_conn"]["type"]]
			tab_body.append(tab_row)
		print(tabulate(tab_body, headers=tab_headers))
	
	def show_connection(self, connkey):
		if connkey == 'all':
			print("**FATAL - no connection key specified. Use --connkey on the command line.\nAvailable connections " )
			sys.exit()
		self.global_config.load_connection()
		try:
			conndic = self.global_config.connection["connections"][connkey]
		except KeyError as key_missing:
			print("**FATAL - wrong connection key specified." )
			self.list_connections()
			sys.exit(2)
		self.global_config.set_conn_vars(conndic)
		
