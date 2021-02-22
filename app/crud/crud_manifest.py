from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.manifest import Manifest
from app.schemas import ManifestInput


class CRUDManifest(CRUDBase[Manifest, ManifestInput, ManifestInput]):
    def create_or_update(self, db: Session, *, obj_in: ManifestInput) -> Manifest:
        db_manifest = db.query(Manifest).get(job_id=obj_in.job_id)

        if db_manifest:
            self.update(db, db_obj=db_manifest, obj_in=obj_in)
        else:
            self.create(db, obj_in=obj_in)


manifest = CRUDManifest(Manifest)
