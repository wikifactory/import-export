# ImportExport service, scope and objectives

This project has been thought as a [FastAPI](https://fastapi.tiangolo.com/) based service. The management of the processing tasks is handled by means of [Celery](https://docs.celeryproject.org/en/stable/getting-started/introduction.html).

The main goal of this service is to allow the users to **import** a certain project (be it software or hardware) from an **import_service** and to **export** it to a target **export_service**.

By *service* we refer to some storage or collaborative editing platforms. Currently, we provide support to the following services:
 - Wikifactory
 - Git / Github
 - Google Drive

By performing the import-export process, the user will have a copy of the project from the import_service inside the export_service. Next, an overview of the process can be found.

# Overview of the Import-Export process

First, the user must select the import service, from where the project will be imported. In order to abstract the process as much as possible, the service requires the URL of the project. This URL will have different meanings given the associated service (e.g. the web address of a github repository or the addres of a project from the Wikifactory platform). At this point, it may be required to perform some authentication or authorization steps, to give the service access to the original files. As the result of this authorization step, a new piece of information is added to the request: the **import_token** and **export_token** .

Next we can see a schema of the request as sent to the ImportExport service, in JSON format:
  

      {
   	    "import_url":"https://github.com/nasa-jpl/open-source-rover",
   	    "import_service":"git",
   	    "import_token":"TOKEN_HERE",
   	    "export_url":"http://wikifactory.com/@dummyuser/imported_rover_project",
   	    "export_service":"wikifactory",
   	    "export_token":"TOKEN_HERE"
       } 

At this point of the implementation we assume that the **export_url** directs to an already created project, be it a github repository, a Google Drive folder or a Wikifactory project

#  Code structure
All the source code can be found inside the `app` folder

 - The `routers` folder includes the `manifests.py` file, in which the allowed REST methods are defined. Those methods launch the appropiate celery tasks, which can be found inside the `celery_tasks.py` file. Finally, the `celery_config.py` and `celery_entrypoint.py` files create the celery app and provide an easy way to integrathe them inside the project.
 - The `model` folder includes the classes that define the model of the app. In order to define those elements, we have taken as inspiration the [Open Know-How](https://app.standardsrepo.com/MakerNetAlliance/OpenKnowHow/wiki/) specification. Let us note that this is still a work-in-progress and hence this data model may change in the near future. There are two important classes defined here: `importer.py` and `exporter.py`. As their name suggests, those abstract classes will be in charge of perform the actual **importing** and **exporting** (more details on this process below).
 - The `controller` folder includes the main actions of the service. In particular, the files `importer_proxy.py`  and `exporter_proxy.py` are in charge of handling the requests sent by the clients. Those components will eventually perform the import and export operations associated with the **import_service** and **export_service**. Finally, inside the `importers` and `exporters` folders you can find the individual importers and exporters, which have an implementation adapted to each target service. More details about how to implement new importers and importes can be found later

# Implementing a new importer or exporter

In order to implement a new **importer**, you have to perform the following steps:

 1. Create the import class inside the `importers` folder. The newly created class must extend from the Importer class. At this point, you can define your own initialization steps, or you can copy the basic schema from any of the already implemented ones. In particular, you have to define the path to which the imported projects will be imported. 
 2. Next, you have to implement the `process_url` method inside the recently created importer taking into account the details of the **import_service**. The result of this process is an instance of a **Manifest**, which holds a reference to all the files included in the project as well as some metadata.
 3. Create the appropiate method in the `importer_proxy.py` file. In this point the service checks the identifier of the **import_service** and dispatch the appropiate importer. That identifier can be defined inside the `app/model/constants.py` file.


The steps required to create a new exporter are similar to those ones, with some minor changes:

 1. The exporter must be created inside the `controller/exporters` folder and it should extend from the *Exporter* class
 2. You have to implement the `export_manifest` method, which is in charge of reading all the files associated to the project and upload them to the **export_service**. To facilitate that process, the *Manifest* class offers the *iterate_through_elements* method. As its name suggests, that methods goes through all the files of the downloaded files of the original project, and it allows you to define callbacks to define how to process each file and folder.
 3. Finally, you have to integrate the exporter into the process by adding an entry inside the `exporter_proxy.py` file that points to the newly created exporter.

