class Job(Base):
    __tablename__ = "jobs"

    job_id = Column(UUID(as_uuid=True), primary_key=True)

    import_service = Column(String)
    import_token = Column(String)
    import_url = Column(String)

    export_service = Column(String)
    export_token = Column(String)
    export_url = Column(String)

    file_elements = Column(Integer)
    processed_elements = Column(Integer)
