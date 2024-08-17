#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This script manages files in the ramdisk used to store the HomeAssistant
    database for faster reading and writing. It is in charge of:
    * copying the db file to the ramdisk mount on Docker startup
    * periodically backing up the db file to persistent storage
    * and archiving old backups to save storage space"""

import os
import shutil
import sqlite3
import sys
import tarfile
import time

from datetime import datetime, timedelta
from pathlib import Path
from pytimeparse import parse


DB_FILENAME: str = os.getenv('DB_FILENAME', 'home-assistant_v2.db')
RAMDISK_PATH: str = os.getenv('RAMDISK_PATH', '/mount/')
STORAGE_PATH: str = os.getenv('STORAGE_PATH', '/storage/')
RAMDISK_DB_PATH: str = RAMDISK_PATH + DB_FILENAME
BACKUP_DB_PATH: str = STORAGE_PATH + DB_FILENAME
BACKUP_DB_COPY_PATH: str = BACKUP_DB_PATH + ".copy"


def start(force_recopy: bool = False) -> bool:
    """Copies the HomeAssistant database from storage to the ramdisk.

    In case of a restart, this function skips the copy operation unless `force_recopy` is `True`.

    Args:
        force_recopy (bool, optional): If `True`, forces a recopy of the database from storage into
                                       the ramdisk. Defaults to False.

    Returns:
        bool: `True` if an existing database is found in the ramdisk mount.
    """

    print('Starting HomeAssistant ramdisk database manager')

    HEALTHCHECK_FLAG_PATH: str = RAMDISK_PATH + 'healthcheck'
    if os.path.exists(HEALTHCHECK_FLAG_PATH):
        Path.unlink(HEALTHCHECK_FLAG_PATH)

    MOUNT_FLAG_PATH: str = RAMDISK_PATH + 'preparing'
    if os.path.exists(MOUNT_FLAG_PATH):
        print('Deleting incompletely copied database')
        Path.unlink(RAMDISK_DB_PATH)
    Path(MOUNT_FLAG_PATH).touch()

    resuming: bool = False
    if not os.path.exists(RAMDISK_DB_PATH) or force_recopy:
        if not os.path.exists(BACKUP_DB_PATH):
            sys.exit('No HomeAssistant DB in storage. Generate one and move it to storage first.')

        print('Copying DB from storage...', end=' ')
        shutil.copy2(BACKUP_DB_PATH, RAMDISK_DB_PATH)
        try:
            os.chmod(RAMDISK_DB_PATH, 0o664)
        except OSError as e:
            print(f"Error changing permissions: {e}")
        print('success')
    else:
        resuming = True
        print('Found existing database, resuming sync')
    
    Path.unlink(MOUNT_FLAG_PATH)
    Path(HEALTHCHECK_FLAG_PATH).touch()

    # Remove incomplete (and potentially corrupt) backup copy.
    if os.path.exists(BACKUP_DB_COPY_PATH):
        Path.unlink(BACKUP_DB_COPY_PATH)
    print('Startup complete')

    return resuming


def sync(
        backup_max_count: int = 10,
        backup_max_age: timedelta = timedelta(days=1)
    ) -> None:
    """Synchronizes the ramdisk database to persistent storage.
    
    This function also manages the archived backups of the database, creating timestamped .tar.gz
    archives of the previous versions. It also limits the number of backups to keep either by count
    or by age.

    *Note: If both `backup_max_count` and `backup_max_age` are supplied, the limit becomes whichever
    of the two arguments yields the smallest number of backups.*

    Args:
        backup_max_count (int, optional): The maximum number of backups to keep. Defaults to 10.
        backup_max_age (datetime, optional): The maximum age of backups to keep. Defaults to 1 day.
    """

    print('Synching ramdisk database to persistent storage...', end=' ')

    # Dump the ramdisk database into a backup copy database
    with (
        sqlite3.connect(RAMDISK_DB_PATH) as ramdisk_db,
        sqlite3.connect(BACKUP_DB_COPY_PATH) as backup_db
    ):
        query: str = "".join(line for line in ramdisk_db.iterdump())
        backup_db.executescript(query)
        ramdisk_db.commit()
        backup_db.commit()

    OLD_BACKUP_DB_PATH = BACKUP_DB_PATH + '.bak'
    if os.path.exists(OLD_BACKUP_DB_PATH):
        Path.unlink(OLD_BACKUP_DB_PATH)

    if os.path.exists(BACKUP_DB_PATH):
        os.rename(BACKUP_DB_PATH, OLD_BACKUP_DB_PATH)
    os.rename(BACKUP_DB_COPY_PATH, BACKUP_DB_PATH)
    print('success')

    print('Archiving old backup databases...', end=' ')
    with tarfile.open(OLD_BACKUP_DB_PATH + '.tar.gz', 'w:gz') as tar:
        tar.add(OLD_BACKUP_DB_PATH)
    
    os.rename(
        OLD_BACKUP_DB_PATH + '.tar.gz',
        OLD_BACKUP_DB_PATH + datetime.now().strftime('-%Y-%-m-%-d-%H:%M:%S') + '.tar.gz'
    )
    Path.unlink(OLD_BACKUP_DB_PATH)
    print('success')

    # Remove all .tar.gz files that exceed the max count or the max age
    print('Removing old backup archives')
    print('Keeping ' + str(backup_max_count) + ' copies', end = ' ')
    print('not more than ' + str(backup_max_age) + ' old')

    def get_modification_date(file_path):
        """Helper function to get the modification time of a file"""
        return os.path.getmtime(os.path.join(STORAGE_PATH, file_path))

    backup_count: int = 0
    files:list[str] = os.listdir(STORAGE_PATH)
    files = sorted(files, key=get_modification_date, reverse=True)
    for file in files:
        file_path = os.path.join(STORAGE_PATH, file)
        if file.endswith('.tar.gz'):
            backup_count += 1
            if (
                backup_count > backup_max_count
                or get_modification_date(file) < (datetime.now() - backup_max_age).timestamp()
            ):
                print('Removed ' + file)
                Path.unlink(file_path)
    print('Sync complete')


def main() -> None:
    FORCE_RECOPY_STR = 'FORCE_RECOPY'
    SYNC_INTERVAL_STR = 'SYNC_INTERVAL'
    BACKUP_COUNT_STR = 'BACKUP_COUNT'
    BACKUP_MAX_AGE_STR = 'BACKUP_MAX_AGE'

    resuming: bool = False
    if FORCE_RECOPY_STR not in os.environ:
        resuming = start()
    else:
        bool_dict: dict[str, bool] = {"true": True, "false": False}
        force_recopy: bool = bool_dict.get(os.getenv(FORCE_RECOPY_STR).lower(), False)
        if force_recopy:
            print('Warning: Starting in force recopy mode!')
        start(force_recopy)

    sync_interval: int = 0
    if SYNC_INTERVAL_STR in os.environ:
        try:
            sync_interval = int(os.getenv(SYNC_INTERVAL_STR))
        except ValueError:
            print('Invalid SYNC_INTERVAL value. Defaulting to 10 minutes.')
    if sync_interval == 0:
        sync_interval = 10

    backup_count: int = 0
    if BACKUP_COUNT_STR in os.environ:
        try:
            backup_count = int(os.getenv(BACKUP_COUNT_STR))
        except ValueError:
            print('Invalid BACKUP_COUNT value. Defaulting to 10.')

    backup_max_age: timedelta = timedelta(seconds=0)
    if BACKUP_MAX_AGE_STR in os.environ:
        parsed_age: any = parse(os.getenv(BACKUP_MAX_AGE_STR))
        if parsed_age is not None:
            backup_max_age = timedelta(seconds=int(parsed_age))
        else:
            backup_max_age = timedelta(days=1)

    def perform_sync() -> None:
        if backup_count and backup_max_age:
            sync(backup_max_count=backup_count, backup_max_age=backup_max_age)
        elif backup_count:
            sync(backup_max_count=backup_count)
        elif backup_max_age:
            sync(backup_max_age=backup_max_age)
        else:
            sync()

    if resuming:
        perform_sync()
    
    print('Starting with a sync interval of ' + str(sync_interval) + ' minute(s)')
    while True:
        time.sleep(sync_interval * 60)
        perform_sync()


if __name__ == "__main__":
    main()