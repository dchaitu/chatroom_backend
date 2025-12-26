from fastapi import Depends
from sqlalchemy.orm import Session
from database import get_db
from storages.rds_storage_implementation import RDSStorageImplementation
from interactors.storage_interfaces.storage_interface import StorageInterface

# Create a single instance of StorageImplementation
def get_storage(db: Session = Depends(get_db)) -> StorageInterface:
    return RDSStorageImplementation(db)
