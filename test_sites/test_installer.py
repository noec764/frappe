import os
import frappe

from frappe.commands.site import _new_site

def get_site_config(site_name):
	site_config = None
	with open('{site_name}/site_config.json'.format(site_name=site_name)) as site_config_file:
		site_config = json.load(site_config_file)
	return site_config

def main():
	site_name = test_site
	site_config = get_site_config(site_name)

	db_type = 'mariadb'
	db_port = site_config.get('db_port', 3306)
	db_host = site_config.get('db_host')
	mariadb_root_username = 'root'
	mariadb_root_password = 'test_dodock'

	frappe.init(site_name, new_site=True)

	_new_site(
		None,
		site_name,
		mariadb_root_username=mariadb_root_username,
		mariadb_root_password=mariadb_root_password,
		admin_password='admin',
		verbose=True,
		install_apps=install_apps,
		source_sql=None,
		force=True,
		db_type=db_type,
		reinstall=False,
		db_host=db_host,
		db_port=db_port,
	)

	mysql_command = 'mysql -h{db_host} -u{mariadb_root_username} -p{mariadb_root_password} -e '.format(
		db_host=config.get('db_host'),
		mariadb_root_username=mariadb_root_username,
		mariadb_root_password=mariadb_root_password
	)

	# update User's host to '%' required to connect from any container
	command = mysql_command + "\"UPDATE mysql.user SET Host = '%' where User = '{db_name}'; FLUSH PRIVILEGES;\"".format(
		db_name=site_config.get('db_name')
	)
	os.system(command)

	# Set db password
	command = mysql_command + "\"ALTER USER '{db_name}'@'%' IDENTIFIED BY '{db_password}'; FLUSH PRIVILEGES;\"".format(
		db_name=site_config.get('db_name'),
		db_password=site_config.get('db_password')
	)
	os.system(command)

	# Grant permission to database
	command = mysql_command + "\"GRANT ALL PRIVILEGES ON \`{db_name}\`.* TO '{db_name}'@'%'; FLUSH PRIVILEGES;\"".format(
		db_name=site_config.get('db_name')
	)
	os.system(command)

	if frappe.redis_server:
		frappe.redis_server.connection_pool.disconnect()

	exit(0)


if __name__ == "__main__":
	main()
