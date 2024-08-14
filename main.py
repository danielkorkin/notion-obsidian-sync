import json
import os
import re

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from markdown2 import markdown
from notion_client import Client
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

load_dotenv()

# Initialize Notion client with an integration token
client = Client(auth=os.getenv("CLIENT_SECRET"))
print("Notion client initialized.")

# Define the Notion page ID directly
materials_notes_page_id = os.getenv("PAGE_ID")


# Retrieve the page object using the official client
def get_page(page_id):
    try:
        return client.pages.retrieve(page_id=page_id)
    except Exception as e:
        print(f"Failed to retrieve the Notion page: {e}")
        exit()


materials_notes_page = get_page(materials_notes_page_id)
print(f"Materials/Notes page retrieved: {materials_notes_page['id']}")

# Define your Obsidian vault path and sync history file
vault_path = os.getenv("VAULT_PATH")
history_file = "synced_files.json"
print(f"Monitoring Obsidian vault at {vault_path}")

# Load or initialize the sync history
if os.path.exists(history_file):
    try:
        with open(history_file, "r") as f:
            sync_history = json.load(f)
    except json.JSONDecodeError:
        print(
            f"Error reading {history_file}. The file might be empty or corrupted. Initializing as an empty dictionary."
        )
        sync_history = {}
else:
    sync_history = {}


def save_sync_history():
    with open(history_file, "w") as f:
        json.dump(sync_history, f, indent=4)


def extract_tags(content):
    # Extract tags from YAML front matter or in-line #tags
    yaml_tags = re.findall(r"tags:\s*\n\s*- ([\w-]+)", content)
    inline_tags = re.findall(r"#([\w-]+)", content)
    tags = yaml_tags + inline_tags

    # Remove YAML front matter from content
    content = re.sub(r"^---[\s\S]*?---", "", content, flags=re.MULTILINE)
    return tags if tags else ["Uncategorized"], content.strip()


def markdown_to_notion_blocks(md_content):
    html_content = markdown(md_content)
    soup = BeautifulSoup(html_content, "html.parser")

    blocks = []
    for element in soup.children:
        if element.name == "h1":
            blocks.append(
                {
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [
                            {"type": "text", "text": {"content": element.get_text()}}
                        ]
                    },
                }
            )
        elif element.name == "h2":
            blocks.append(
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [
                            {"type": "text", "text": {"content": element.get_text()}}
                        ]
                    },
                }
            )
        elif element.name == "h3":
            blocks.append(
                {
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [
                            {"type": "text", "text": {"content": element.get_text()}}
                        ]
                    },
                }
            )
        elif element.name == "p":
            blocks.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {"type": "text", "text": {"content": element.get_text()}}
                        ]
                    },
                }
            )
        # Add more elements as needed (e.g., lists, quotes)

    return blocks


def clear_notion_page(page_id):
    # Fetch all children blocks of the page and delete them
    children = client.blocks.children.list(block_id=page_id)["results"]
    for child in children:
        client.blocks.delete(block_id=child["id"])
    print(f"Cleared existing content from page ID: {page_id}")


def find_or_create_page(title, parent_id):
    # Find if a page with the given title exists under the parent
    children = client.blocks.children.list(block_id=parent_id)["results"]
    for child in children:
        if child["type"] == "child_page" and "title" in child["child_page"]:
            if child["child_page"]["title"] == title:
                return child["id"]

    # If not found, create a new page
    new_page = client.pages.create(
        parent={"page_id": parent_id},
        properties={"title": [{"text": {"content": title}}]},
    )
    print(f"Created new page: {title}")
    return new_page["id"]


def sync_note_to_notion(note_path):
    note_path = str(note_path)
    print(f"Syncing note: {note_path}")
    with open(note_path, "r", encoding="utf-8") as mdFile:
        content = mdFile.read()

    # Extract tags and clean content
    tags, content = extract_tags(content)
    print(f"Tags found: {tags}")

    # Extract the note title from the filename
    note_title = os.path.splitext(os.path.basename(note_path))[0]
    print(f"Note title: {note_title}")

    current_page_id = materials_notes_page_id

    for tag in tags:
        # Find or create subpage with tag name
        current_page_id = find_or_create_page(tag, current_page_id)

    # Find or create note page with note title
    note_page_id = find_or_create_page(note_title, current_page_id)

    # Clear existing content before appending new content
    clear_notion_page(note_page_id)

    # Convert markdown content to Notion blocks and upload it
    blocks = markdown_to_notion_blocks(content)
    client.blocks.children.append(block_id=note_page_id, children=blocks)
    print(f"Uploaded content to page: {note_title}")

    # Update sync history
    sync_history[note_path] = os.path.getmtime(note_path)
    save_sync_history()


class VaultEventHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith(".md"):
            print(f"Detected change in file: {event.src_path}")
            sync_note_to_notion(event.src_path)
        elif event.src_path.endswith(".excalidraw"):
            # Handle Excalidraw files if necessary
            pass


def sync_existing_files():
    print("Syncing existing files...")
    for root, dirs, files in os.walk(vault_path):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                last_modified = os.path.getmtime(file_path)
                if (
                    file_path not in sync_history
                    or sync_history[file_path] < last_modified
                ):
                    sync_note_to_notion(file_path)


if __name__ == "__main__":
    sync_existing_files()  # Sync any unsynced files on startup

    event_handler = VaultEventHandler()
    observer = Observer()
    observer.schedule(event_handler, path=vault_path, recursive=True)
    observer.start()

    print("Observer started. Monitoring for changes...")

    try:
        while True:
            observer.join(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
