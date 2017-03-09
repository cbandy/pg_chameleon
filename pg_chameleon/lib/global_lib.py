import yaml
import sys
import os
from tabulate import tabulate
import logging
from pg_chameleon import pg_engine
from daemonize import Daemonize
	
		
class replica_logging(object):
	def __init(self):
		self.logger=None

	def init_logger(self, log_dest,log_level,log_append, log_dir, connkey):
		"""
			
		"""
		log_file= '%s/%s.log' % (log_dir,connkey)
		log_file = os.path.expanduser(log_file)
		self.logger = logging.getLogger(__name__)
		self.logger.setLevel(logging.DEBUG)
		self.logger.propagate = False
		formatter = logging.Formatter("%(asctime)s: [%(levelname)s] - %(filename)s: %(message)s", "%b %e %H:%M:%S")
		
		if log_dest=='stdout':
			fh=logging.StreamHandler(sys.stdout)
			
		elif log_dest=='file':
			if log_append:
				file_mode='a'
			else:
				file_mode='w'
			fh = logging.FileHandler(log_file, file_mode)
		
		if log_level=='debug':
			fh.setLevel(logging.DEBUG)
		elif log_level=='info':
			fh.setLevel(logging.INFO)
			
		fh.setFormatter(formatter)
		self.logger.addHandler(fh)
		return fh


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
		local_conndir= "%s/.pg_chameleon/connection/" % os.path.expanduser('~')	
		
		if connection_file:
			self.connection_file = '%s/%s'%(local_conndir, connection_file)
			if load_config:
				self.load_config()
		else:
			print("**FATAL - invalid connection file specified **\Expected filename got %s." % (self.connection_file))
			sys.exit(1)
		self.lst_skip=["src_conn", "dest_conn", "connections"]
		self.conn_pars={}
		self.log_kwargs={}
		
	def set_log_kwargs(self, connkey = "all"):
		self.load_connection()
		log_pars = ['log_dest','log_level','log_append', 'log_dir']
		for par in log_pars:
			self.log_kwargs[par] = self.conn_pars[par]
		self.log_kwargs["connkey"] = connkey
	
	def set_copy_max_memory(self):
		copy_max_memory = str(self.conn_pars["copy_max_memory"])[:-1]
		copy_scale=str(self.conn_pars["copy_max_memory"] )[-1]
		try:
			int(copy_scale)
			copy_max_memory = self.conn_pars["copy_max_memory"]
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
		self.conn_pars["copy_max_memory"] = copy_max_memory
	
	
	def set_conn_vars(self, connkey):
		
		self.currentconn= self.connection["connections"][connkey]
		self.conn_pars["connections"] = None
		for key in self.currentconn:
			self.conn_pars[key] = self.currentconn[key]
			if key not in self.lst_skip:
				print('Override value key %s to %s' % (key, self.currentconn[key]))
		self.set_copy_max_memory()	
		self.conn_pars["pid_dir"] = os.path.expanduser(self.conn_pars["pid_dir"])
		
		
	
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
			self.conn_pars[key] = conndic[key]
		self.set_copy_max_memory()	
		
		

class replica_engine(object):
	def __init__(self, conn_file):
		self.global_config = global_config(conn_file)
		self.pg_eng=pg_engine()
		
	def create_service_schema(self, connkey):
		if connkey == 'all':
			print('You should specify a connection key')
			self.list_connections()
		else:
			
			self.global_config.set_log_kwargs(connkey)
			replog = replica_logging()
			fh = replog.init_logger(**self.global_config.log_kwargs)
			keep_fds = [fh.stream.fileno()]
			self.global_config.set_conn_vars(connkey)
			pid='%s/%s.pid' % (self.global_config.conn_pars["pid_dir"], connkey)
			self.pg_eng.conn_pars=self.global_config.conn_pars
			self.pg_eng.logger=replog.logger
			self.pg_eng.create_service_schema()
			#daemon = Daemonize(app="test_app", pid=pid, action=self.pg_eng.create_service_schema, foreground=True, keep_fds=keep_fds)
			#daemon.start()
	
			
	
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
		tab_body=[]
		if connkey == 'all':
			print("**FATAL - no connection key specified. Use --connkey on the command line.\nAvailable connections " )
			sys.exit()
		self.global_config.load_connection()
		try:
			self.global_config.set_conn_vars(connkey)
		except KeyError:
			print("**FATAL - wrong connection key specified." )
			self.list_connections()
			sys.exit(2)
		
		tab_headers=["Parameter", "Value"]
		for conn_par in self.global_config.conn_pars:
			if conn_par not in self.global_config.lst_skip:
				tab_row=[conn_par, self.global_config.conn_pars[conn_par]]
				tab_body.append(tab_row)
		print(tabulate(tab_body, headers=tab_headers))
			
		
