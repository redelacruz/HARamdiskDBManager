![Home Assistant](https://img.shields.io/badge/home%20assistant-%2341BDF5.svg?style=for-the-badge&logo=home-assistant&logoColor=white)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![SQLite](https://img.shields.io/badge/sqlite-%2307405e.svg?style=for-the-badge&logo=sqlite&logoColor=white)

# Home Assistant RAM Disk Database Manager

The Home Assistant RAM Disk Database Manager offers a dead simple way to manage a Home Assistant recorder SQLite database on a RAM disk – and by "dead simple," I mean it's very barebones rather than very easy to use. That doesn't mean that it's very hard to use either, because once set up, it's meant to be relatively fire and forget.

I created this project for a simple reason: I was running my Home Assistant instance on an old laptop with a slow hard disk drive and it was taking forever to load historical entity data, which I needed to help me develop scripts for my automation projects. Because the laptop had way more memory than it was using running my self-hosted services, it felt like a good idea to move the recorder database to memory.

Unfortunately, Home Assistant doesn't support in-memory SQLite databases [due to thread safety concerns](https://github.com/home-assistant/core/pull/69616). I fully accepted this risk, however, but because the Home Assistant team already closed any possibility of using in-memory SQLite databases, I had to find a way around it.

If you find yourself in a similar situation and are fully accepting of the risks, then the Home Assistant RAM Disk Database Manager might be able to help.

## How It Works
The Home Assistant RAM Disk Database Manager does 4 basic things:
1. It copies a backup of the recoder database in persistent storage (a hard drive, SD card or SSD) to the RAM disk at system startup.
2. At configurable intervals, it uses the `iterdump()` function from Python's `sqlite3` library to clone the database on the RAM disk to persistent storage.
3. It backs up old copies of the database into timestamped `.tar.gz` archives to save space while giving you fallback options.
4. It deletes old archived copies based on count or age to prevent it from filling up your persistent storage device with unnecessary backups.

## ❗This Is Your Final Warning❗
Do not use this app if you aren't prepared to accept that you *might* lose some data or crash your system as a result of it.

It does not:
* do anything to alleviate thread safety concerns.
* guarantee that your backups will be free of state inconsistencies.
* check that you aren't completely filling up your device's memory, which can crash your system[^1].
* check that you aren't completely filling up your device's persistent storage, which can slow your system down or crash it[^2].
* check that your database isn't starting to fill up the allocated maximum size of your ram disk [^3].

[^1]: You can prevent this by limiting the maximum size of your ram disk.
[^2]: It already sort of does this by limiting the number of backups it keeps based on whether count or age results in the least amount of archived backups. However, it will not check that you have enough free space to handle a clone of the database when it starts the copy operation.
[^3]: You can control this by adjusting your Home Assistant's recorder options.

***Note:** I may add features that limit the impact of these caveats in the future.*

