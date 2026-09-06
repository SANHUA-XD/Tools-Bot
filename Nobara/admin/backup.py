import os
import json
import asyncio
import shutil
from bson import json_util
from pytz import timezone
from pyrogram import Client, filters
from pyrogram.types import Message
from pymongo import MongoClient
from config import config
from Nobara import app, log, BACKUP_FILE_JSON, scheduler
from Nobara.database import MCL
from Nobara.decorator.errors import error
from Nobara.decorator.save import save


# NOTE: This used to shell out to the "mongodump"/"mongorestore" CLI tools via
# subprocess. Those aren't installed on Heroku (they're a separate MongoDB
# Database Tools package, not part of the Python buildpack), which crashed
# every scheduled backup with FileNotFoundError: 'mongodump'. Backups are now
# done in pure Python via pymongo, so no external binary is required anywhere.

def _dump_database(mongo_db, out_dir: str):
    """Dumps every collection in a pymongo Database into JSON files."""
    os.makedirs(out_dir, exist_ok=True)
    for coll_name in mongo_db.list_collection_names():
        docs = list(mongo_db[coll_name].find({}))
        with open(os.path.join(out_dir, f"{coll_name}.json"), "w", encoding="utf-8") as f:
            json.dump(docs, f, default=json_util.default, ensure_ascii=False)


def _restore_database(mongo_db, in_dir: str):
    """Restores every *.json file in in_dir back into its matching collection."""
    for filename in os.listdir(in_dir):
        if not filename.endswith(".json"):
            continue
        coll_name = filename[:-5]
        with open(os.path.join(in_dir, filename), encoding="utf-8") as f:
            docs = json.load(f, object_hook=json_util.object_hook)
        if docs:
            mongo_db[coll_name].delete_many({})
            mongo_db[coll_name].insert_many(docs)


# Database backup function - dumps the main DB, and the dedicated filter DB
# too (if it's actually a separate cluster/database from the main one).
def backup_db(path: str) -> str:
    try:
        if os.path.exists(path):
            shutil.rmtree(path)
        os.makedirs(path, exist_ok=True)

        _dump_database(MCL[config.DATABASE_NAME], os.path.join(path, "main"))

        filter_uri = config.FILTER_MONGODB_URI or config.MONGODB_URI
        filter_db_name = config.FILTER_DATABASE_NAME or config.DATABASE_NAME
        if filter_uri != config.MONGODB_URI or filter_db_name != config.DATABASE_NAME:
            filter_client = MongoClient(filter_uri)
            try:
                _dump_database(filter_client[filter_db_name], os.path.join(path, "filters"))
            finally:
                filter_client.close()

        shutil.make_archive(path, 'zip', path)
        return f"{path}.zip"
    except Exception as e:
        return f"Backup failed: {str(e)}"


def restore_db(zip_path: str) -> str:
    try:
        extract_path = zip_path.replace(".zip", "")
        if os.path.exists(extract_path):
            shutil.rmtree(extract_path)
        shutil.unpack_archive(zip_path, extract_path)

        main_dir = os.path.join(extract_path, "main")
        if os.path.isdir(main_dir):
            _restore_database(MCL[config.DATABASE_NAME], main_dir)

        filters_dir = os.path.join(extract_path, "filters")
        if os.path.isdir(filters_dir):
            filter_uri = config.FILTER_MONGODB_URI or config.MONGODB_URI
            filter_db_name = config.FILTER_DATABASE_NAME or config.DATABASE_NAME
            filter_client = MongoClient(filter_uri)
            try:
                _restore_database(filter_client[filter_db_name], filters_dir)
            finally:
                filter_client.close()

        shutil.rmtree(extract_path, ignore_errors=True)
        return "Restore successful!"
    except Exception as e:
        return f"Restore failed: {str(e)}"


async def handle_backup(client: Client, message: Message):
    path = f"./backup/{config.BOT_NAME}"
    zip_path = await asyncio.to_thread(backup_db, path)
    if zip_path.endswith(".zip"):
        await client.send_document(chat_id=config.OWNER_ID, document=zip_path)
        shutil.rmtree(path, ignore_errors=True)  # Clean up the backup directory
        os.remove(zip_path)  # Clean up the zip file
        response = "Backup successful!"
    else:
        response = zip_path
    await message.reply_text(response)

async def handle_restore(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply_text("Please reply to a backup zip file to restore.")
        return

    document = message.reply_to_message.document
    file_path = await client.download_media(document.file_id)
    response = await asyncio.to_thread(restore_db, file_path)
    os.remove(file_path)  # Clean up the downloaded zip file
    await message.reply_text(response)

@app.on_message(filters.command("backup", prefixes=config.COMMAND_PREFIXES) & filters.user(config.OWNER_ID))
@error
@save
async def backup_command(client: Client, message: Message):
    await handle_backup(client, message)

@app.on_message(filters.command("restore", prefixes=config.COMMAND_PREFIXES) & filters.user(config.OWNER_ID))
@error
@save
async def restore_command(client: Client, message: Message):
    await handle_restore(client, message)

# Automatic backup function
async def scheduled_backup():
    path = f"./backup/{config.BOT_NAME}"
    try:
        zip_path = await asyncio.to_thread(backup_db, path)
        if zip_path.endswith(".zip"):
            message = await app.send_document(chat_id=config.LOG_CHANNEL, document=zip_path)
            shutil.rmtree(path, ignore_errors=True)  # Clean up the backup directory
            os.remove(zip_path)  # Clean up the zip file

            # Save the file ID to a JSON file
            with open(BACKUP_FILE_JSON, "w") as f:
                json.dump({"file_id": message.document.file_id}, f)

            log.info("Backup completed and file ID saved.")
        else:
            log.error(f"Scheduled backup failed: {zip_path}")
    except Exception as e:
        log.error(f"Scheduled backup raised an exception: {e}")


scheduler.add_job(scheduled_backup, "cron", hour=0, minute=0, timezone=timezone("Asia/Kolkata"))
