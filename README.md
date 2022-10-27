# Railcron

A [Prefect 2.0](https://www.prefect.io/opensource/v2/) based system for fetching data from
[Network Rail Open Data](https://wiki.openraildata.com//index.php?title=Main_Page) sources.

Railcron currently only handles the fetch and archive step of getting the data (e.g. train timetables) that Network Rail
publishes daily or periodically.

The Prefect flows must be enhanced or additional ones created to perform subsequent ETL processes (e.g. into a database).

### Installation

**Currently UNIX/BSD focused, Windows not supported yet**

1. Clone the Railcron repository
2. Create a virtual environment (e.g. python -m venv --prompt Railcron venv) and activate it
3. pip install -r requirements.txt
4. Read the [Prefect documentation](https://docs.prefect.io/) especially that about deployments.

### Configuration

All of the configuration is first handled through the YAML configuration file (railcron.yml). Each section, except for the
first three, is configuration info for a flow that fetches specific data.

1. Copy master_railcron.yml file to railcron.yml
2. Depending on what services you want to use, create accounts on the [National Rail Opendata](https://opendata.nationalrail.co.uk/)
and/or [Network Rail's Data Feeds](https://datafeeds.networkrail.co.uk/ntrod/login) websites.
3. Edit the railron.yml file (it is well commented). For each service you want to interact with, configure the relevant section.
You can comment out an entire section for a flow that is not being used.
4. Make sure to configure the first two sections with the relevant Opendata and/or Datafeed account information.
Also make sure to update the "settings" section to enable rsync or email if desired.
5. Make sure to set the "archive_path" settings in each section to point to the root directory where files are stored. If rsync is
to be used, edit the 'rsync' command strings as needed. Most other settings do not needed editing, but double check them.
5. AWS keys must be gotten from the accounts you created or relevant info found by searching the Open Rail Data Google group.

You then have two choices:

**YAML configuration file**

This method will use the YAML configuration file and have flows read it every time they are executed

This is convenient if you want to be able to dynamically update how a flow operates without having to stop a flow,
recreate the deployment, etc - this is useful for debugging.

"RAILCRON_CFG" is an optional environment variable that specifies the directory where the railcron.yml file can be found.
For example, if this is set to "/tmp" then a flow would look for the railcron.yml file in /tmp.

Its default value is "." meaning the railcron.yml will be bundled with the deployment created for a flow. But this is not
very useful because if the configuration settings need changed, the deployment will have to be stopped and recreated after
updating the file. Using RAILCRON_CFG will avoid this hassle.

**Prefect Blocks**

This method will create Prefect Blocks out of the YAML configuration file and then settings can be edited through the Prefect UI.

```
python make_blocks.py
```
will read the configured YAML file and then register and create Blocks that can be edited through the UI. The flows will first try
to use these blocks before resorting to reading the YAML file. Currently, Prefect does not support validation of the configuration
information in a Block, so do double check what is entered.


### Deployments

Flows must first be instantiated before they can be executed. "make_deployments.sh" is a script that will create deployment files and
save them into ./deplayments/. They then can be edited/updated as needed (e.g. to set the RAILCRON_CFG variable) before the deployment
is applied to the Prefect database.

**Read and edit the make_deployments.sh script before executing it**


### Flow Execution

1. Read and execute "setup_prefect.sh" - it will create and configure Prefect profiles (the dryrun one is useful for debugging).
2. Start the Prefect server (see setup_prefect.sh).
3. Create the 'daily' work queue.
4. Run "make_deployments.sh apply" install the deployments to the database.
5. Once installed, the flows can be further configured through the UI to run at the desired times.


#### Notes

Every time a new file has been fetched, a JSON Block is updated with the path of this new file. The motivation for this is to enable
flows to not be explicitly coupled, but loosely coupled, as well as running on two different servers while communicating through a
single database (i.e. server 1 fetches files, server 2 with more CPUs processes the large ones).
Refer to the function "update_newfile_block()" for more information.


### TODO

* Subsequent flows to process data into Postgresql/HDFS
* Support fetching of DARWIN FTP files
* Support OpenLDBSVWS
* Support Windows environment
