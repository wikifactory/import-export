
# ImportExport service, scope and objectives

 
The main goal of this service is to allow the users to **import** a certain project (be it software or hardware) from an **import_service** and  **exporting** it to a target **export_service**.

By *service* we refer to some storage or collaborative editing platforms. Currently, we provide support to the following services:

- Wikifactory
- Git / Github
- Google Drive
  
Once the import-export process has finished, the user will have a copy of the project from the **import_service** inside the **export_service**. 

This project has been thought as a [FastAPI](https://fastapi.tiangolo.com/) based service. The structure of the code follows the specification defined [here](https://fastapi.tiangolo.com/project-generation/). 
The management of the processing tasks is handled by means of [Celery](https://docs.celeryproject.org/en/stable/getting-started/introduction.html).
[PostgreSQL](https://www.postgresql.org/) has been used as the database provider.

Next, an overview of the process can be found.

# Overview of the Import-Export process

  

First, the user must select the source project that will be imported. 
In order to abstract the process as much as possible, the ImportExport service requires the URL of the source project. This URL will have different meanings given the associated service and will have an asssociated **import_service** (e.g. the web address of a github repository or the addres of a project in Wikifactory). 
It may be required to perform some authentication or authorization steps, to provide the ImportExport service access to the original files or to the target platform. As the result of this step, a new piece of information can be integrated into the request: the **import_token** and **export_token** .

 
Below, we provide a schema of the request as must be sent to the ImportExport service, in JSON format:

	{

	"import_url":"https://github.com/nasa-	jpl/open-source-rover",
	"import_service":"git",
	"import_token":"TOKEN_HERE",
	"export_url":"http://wikifactory.com/@dummyuser/imported_rover_project",
	"export_service":"wikifactory",
	"export_token":"TOKEN_HERE"

	}

  

At this point of the implementation we assume that the **export_url** directs to an already created project, be it a github repository, a Google Drive folder or a Wikifactory project.

  

# Code structure

All the source code associated to the IEService can be found inside the `app` folder

 

- The `api` folder holds the information of the API exposed by the service. In particular, the folder `api_v1` contents the current exposed api. Later, more versions of the API could be added inside this folder. In any case, the `api.py` file define the paths exposed by the service 

- The `core` folder is in charge of two main functionalities. First, it configures the details of the Celery tasks with the `celery_app` file. Second, with the `config.py` file it defines the most basic information of the service (e.g. where the downloaded files will be stored or the credentials to access the data base). 
- The logic of importing and exporting for each service is defined inside the `importers` and `exporters` folder. Each individual importer inherits from **BaseImporter**, which defines its basic functionallity. Exporters have an equivalent process, but descending from **BaseExporter**.

The following folders inside the `app` one are strongly related with the data model of the service:
- The `db` folder holds the required information of the db associated to the IEService. More in detail, the `init_db.py` file is in charge of initializing the db (i.e. creating the tables), and this is done by reading all the classes defined in `base.py`. Finally, the db session is created inside `session.py`, from where the rest of the service will have access. 

- The data model of the service is defined inside the `schemas` folder. Each entity in the service is defined by a class that inherits from Pydantics' BaseModel ([more info here](https://pydantic-docs.helpmanual.io/usage/models/)). Pydantics is seamless integrated inside FastAPI and allows automatic validation.

- The `models` folder on its behalf, defines how those schemas will be represented inside the database. This definition is based on the [sqlalchemy](https://www.sqlalchemy.org/) toolkit.

- Finally, iside the `crud` folder we defined the main methods used to create, read update and delete (CRUD) the elements inside the database. This `crud` module is used across the IEService to access the data inside the db as well as updating it.


# Implementing a new importer or exporter

  

In order to implement a new **importer**, the following steps are required:


1. Create the import class inside  `app/importers`. The newly created class must extend from **BaseImporter**. At this point, you can define your own initialization steps, or you can copy the basic schema from any of the already implemented ones. 

2. Next, you have to implement the `process` method inside your importe,r taking into account the details of the **import_service**. As the result of this process, a **Manifest** instance will be created in the db and the files will be downloaded in the computer.

3. Create the service entry in the `app/importers/__init__.py` file. Inside this file, first you must set the string identifier of your service (e.g. "git" or "google_drive"). After that, you must add an entry to the validator map, which ties that same service identifier to an associated URL validator. 

The steps required to create a new exporter are similar to those ones, with some minor changes:


1. The exporter must be created inside the `app/exporters` folder and it should extend from the *BaseExporter* class

2. You have to implement the `process` method, which is in charge of reading all the files associated to the project and upload them to the **export_service**.

3. Finally, you have to integrate the exporter into the process by adding an entry inside the validator map defined in `app/exporters/__init__.py` as well as the service identifier.


# Running

You can run the service by doing: `docker-compose up -d` and stop it by using `docker-compose down`. This will start the service in the background.

By default, the access to the database has been disabled (i.e. not exposed). If you want to access directly to that data, you must change the `docker-compose.override.yaml` file. In particular, you must expose the db port inside your computer. For example, you could do this:

``` networks:
      - default
    ports: 				# Add this line
      - "8004:5432"		# Add this line
```

  
# Testing

You can run the tests inside the docker environment by using the following command:

`docker-compose run backend pytest`

