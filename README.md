![Home Assistant](https://img.shields.io/badge/home%20assistant-%2341BDF5.svg?style=for-the-badge&logo=home-assistant&logoColor=white)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![SQLite](https://img.shields.io/badge/sqlite-%2307405e.svg?style=for-the-badge&logo=sqlite&logoColor=white)

# Home Assistant RAM Disk Database Manager

The Home Assistant RAM Disk Database Manager offers a dead simple way to manage a Home Assistant recorder SQLite database on a RAM disk – and by "dead simple," I mean it's very barebones rather than very easy to use. That doesn't mean that it's very hard to use either, because once set up, it's relatively fire and forget.

I created this project for a simple reason: I was running my Home Assistant instance on an old laptop with a slow hard disk drive and it was taking forever to load historical entity data, which I needed to help me develop scripts for my automation projects. Because the laptop had way more memory than it was using running my self-hosted services, it felt like a good idea to move the recorder database to memory.

Unfortunately, Home Assistant doesn't support in-memory SQLite databases [due to thread safety concerns](https://github.com/home-assistant/core/pull/69616). I fully accepted this risk, but because the Home Assistant team already closed any possibility of using in-memory SQLite databases, I had to find a way around it.

If you find yourself in a similar situation and are also fully accepting of the risks, then the Home Assistant RAM Disk Database Manager might be able to help.

## How It Works
The Home Assistant RAM Disk Database Manager does 4 basic things:
1. It copies a backup of the recoder database in persistent storage (a hard drive, SD card or SSD) to the RAM disk at system startup.
2. At configurable intervals, it uses the `iterdump()` function from Python's `sqlite3` library to clone the database on the RAM disk to persistent storage.
3. It backs up old copies of the database into timestamped `.tar.gz` archives to save space while giving you some fallback options.
4. It deletes old archived copies based on count or age to prevent it from filling up your persistent storage device with unnecessary backups.

## ❗This Is Your Final Warning❗
Do not use this app if you aren't prepared to accept that you *might* lose some data or crash your system as a result of it. Be prepared to perform your own recovery if something unwanted happens.

This app does **NOT**:
* do anything to alleviate thread safety concerns.
* guarantee that your backups will be free of state inconsistencies.
* check that you aren't completely filling up your device's memory, which can crash your system[^1].
* check that you aren't completely filling up your device's persistent storage, which can slow your system down or crash it[^2].
* check that your database isn't starting to fill up the allocated maximum size of your ram disk [^3].
* automatically retrieve backups from the `.tar.gz` files it creates in case the latest backup is unusable.

[^1]: You can prevent this by limiting the maximum size of your ram disk.
[^2]: It already sort of does this by limiting the number of backups it keeps based on whether count or age results in the least amount of archived backups. However, it will not check that you have enough free space to handle a clone of the database when it starts the copy operation.
[^3]: You can control this by adjusting your Home Assistant's recorder options.

By ignoring this warning and using this app, you agree that you and you alone are accountable for any issues that arise because of it.

***Note:** I may add features that limit the impact of these caveats in the future. In the meantime, I plan to add guides to the project wiki for mitigating some of these risks.*

## Compatibility
This app was tested against the following Home Assistant implementations:
#### Home Assistant Container
Core versions:
* 2024.3.1 ✔️

#### Home Assistant Core
Untested

#### Home Assistant Supervised
Untested

## Usage
This guide assumes that you are running Home Assistant in a Docker container with compose. If you aren't, then you will have to adjust how you set up the app accordingly.

### 1. Create and mount a RAM disk
Start by checking if you have enough RAM to dedicate to storing your recoder database by running the following command in your host system:
```
free -h
```
Ideally, the available memory should be at least 2.5x the size of your database *(you can ignore this at your own risk)*.

If you have enough memory available, create a directory to use as your mount point. For consistency's sake, this guide will use `/mnt/ha_database` as the mount point.
```
mkdir -p /mnt/ha_database
```

Then, add an entry for the RAM disk in your `/etc/fstab` file by adding the following lines:
```
# Ramdisk for Home Assistant database
tmpfs    /mnt/ha_database    tmpfs    nodev,nosuid,noexec,nodiratime,size=2048M    0    0
```
Adjust the size and mounting location of the file system to fit your preference and system characteristics.

After saving the changes to your `/etc/fstab` file run
```
mount -a
```
to mount the `tmpfs` file system.

>I highly recommend using `tmpfs` rather than `ramfs` when using this app due to the size restrictions that `tmpfs` can impose. If your database grows too large, using `ramfs` can completely fill your available memory and deadlock your system

Finally, run
```
df -h
```
to confirm that your file system is mounted at the correct location and has the correct maximum size.

#### Why not use `/dev/shm` instead?
The `/dev/shm` mount is a `tmpfs` file system often used for storing temporary files. However, its presence is not guaranteed. Often, it is there simply as a side-effect of some process calling `shm_open()`.

Additionally, there is some evidence that suggests that using `/dev/shm` for the Home Assistant database [no longer works](https://community.home-assistant.io/t/recorder-db-in-ram/715912).

Creating our own RAM disk ensures we have a consistently available mount to use with Home Assistant and this app.

### 2. Move the Home Assistant database to the RAM disk and mount it as a container volume
Before continuing, you will have to stop your Home Assistant instance. You can do this with compose by running
```
docker compose stop homeassistant
```
in the same directory your `compose.yaml` file is in. The above assumes that your container is named `homeassistant`, so if it isn't, change the container name accordingly.

After home stopping your instance, backup your database so that you can revert it in case anything goes wrong:
```
cp /homeassistant/config/dir/homeassistant_v2.db /homeassistant/config/dir/homeassistant_v2.db.bak
```

Then, copy the recorder database from your Home Assistant's `config` directory into your RAM disk's file system:
```
cp /homeassistant/config/dir/homeassistant_v2.db /mnt/ha_database/
```
In your `compose.yaml` file, add your RAM disk mount point as a volume. For example:
```
volumes:
  - ./homeassistant/config:/config
  - /etc/localtime:/etc/localtime:ro
  - /mnt/ha_database:/config/database # RAM disk mount point
```
> As you can see in the above example, the RAM disk is mounted as nested directory named `database` within the `config` folder. This is the recommended approach, as mounting just the database file can be iffy, especially when you need to recreate it due to how Docker handles file mounts if the source file is missing in the host.

If you used the directory-mounting approach shown above, you will have to adjust your `configuration.yaml` file so that the recorder knows where to find the database by adding these lines to it:
```
recorder:
  db_url: sqlite:////config/database/home-assistant_v2.db
```
Recreate your Home Assistant container so that it uses the new volume mount point:
```
docker compose up -d
```
If all went well, Home Assistant should start as normal. And, as you navigate through the interface, you'll find that components that rely on the recorder database (such as data in History) load faster than before.

### 3. Build and run the Home Assistant RAM Disk Database Manager
Finally, we build and run this app. The easiest way to do this is by adding it as a service in your `compose.yaml` file:
```
homeassistant_db:
  container_name: homeassistant_db
  build: https://github.com/redelacruz/HARamdiskDBManager.git
  volumes:
    - /mnt/ha_database:/mount
    - ./ha-ramdb-manager/data:/storage
  restart: unless-stopped
```
Additionally, add the `depends_on` attribute to your Home Assistant service:
```
homeassistant:
  container_name: homeassistant
  depends_on:
    homeassistant_db:
      condition: service_healthy
      restart: false
  # other configuration attributes continue below...
```
The `depends_on` attribute will cause the Home Assistant service to delay its start until after the RAM Disk Database Manager has fully copied the database. The `restart: false` attribute ensures that Home Assistant does not also restart if the Database Manager restarts for whatever reason.

Given the above, the `compose.yaml` file should look similar to the [sample Docker compose file](#sample-docker-compose-file) included below.

With that set, use
```
docker compose up -d
```
to build the Home Assistant RAM Disk Database Manager service and recreate the Home Assistant service (this will cause Home Assistant to restart).

Check that the app started correctly by inspecting the logs from its container. If all went well (and assuming the default options were used), they should look something like this:
```
Starting
Starting HomeAssistant ramdisk database manager
Found existing database, resuming sync
Startup complete
Synching ramdisk database to persistent storage... success
Archiving old backup databases... success
Removing old backup archives
Keeping 10 copies not more than 1 day, 0:00:00 old
Sync complete
Starting with a sync interval of 10 minute(s)
```
It's also a good idea to periodically check the logs of your Home Assistant service for database errors after setup.

If you ever need to rebuild the Home Assistant RAM Disk Database Manager, you can use
```
docker compose up -d --build homeassistant_db
```
to do so.

## Sample Docker Compose File
```
services:
  homeassistant_db:
    container_name: homeassistant_db
    build: https://github.com/redelacruz/HARamdiskDBManager.git
    volumes:
      - /mnt/ha_database:/mount
      - ./ha-ramdb-manager/data:/storage
    restart: unless-stopped
  homeassistant:
    container_name: homeassistant
    image: ghcr.io/home-assistant/home-assistant:stable
    depends_on:
      homeassistant_db:
        # delays Home Assistant startup until after the database is fully copied
        condition: service_healthy
        restart: false
    volumes:
      - ./homeassistant/config:/config
      - /etc/localtime:/etc/localtime:ro
      - /mnt/ha_database:/config/database
    restart: unless-stopped
    privileged: true
    network_mode: host
```

## Environment Variables
The following environment variables (listed with their default values) allow you to control the behavior of The Home Assistant RAM Disk Database Manager:

**`FORCE_RECOPY`**: `false`\
Forces the app to copy the database in persistent storage to the RAM disk at startup. This can be used to revert to a backup in the in-memory database gets corrupted.\
***IMPORTANT!** Remember to set this to false after using it. Otherwise, you might cause the database on the RAM disk to be overwritten during a container restart. This can be very bad especially if Home Assistant is writing to the database as you're doing this.*

**`SYNC_INTERVAL`**: `10`\
In minutes, this environment variable sets how often the app will try to clone the database in the RAM drive to persistent storage. Setting this to 0 will cause it to default back to 10.

**`BACKUP_COUNT`**: `10`\
Sets how many backups of the database the app will try to keep. If `BACKUP_MAX_AGE` results in a lesser number of backups, `BACKUP_COUNT` has essentially no effect.

**`BACKUP_MAX_AGE`**: `1 day`\
Sets how old backups can get before they are deleted. Any string parsable by [pytimeparse](https://github.com/wroberts/pytimeparse?tab=readme-ov-file#pytimeparse-time-expression-parser) will be accepted. If `BACKUP_COUNT` results in a lesser number of backups, `BACKUP_MAX_AGE` has essentially no effect.

**`USE_ROOT`**: `false`\
Allows the app to use `sudo` elevation in order to copy and store the database as root. Do not use this option without first verifying that the app works without it.\
*Note: You likely won't need `USE_ROOT` even if your Home Assistant implementation runs as root in a privileged Docker container. The app only uses read operations for copying, so root is not needed to clone the database into backup.\
You might need `USE_ROOT` if you modified the permissions of the recorder database to deny non-root users read access to it or if your Home Assistant implementation runs as a non-root, non-`1000:1000` user.*