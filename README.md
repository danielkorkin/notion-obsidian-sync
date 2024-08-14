# Obsidian sync to Notion

## Getting Started

### 1. Connect to Notion 

- Go to [Integrations Portal](https://www.notion.so/profile/integrations)
- Click on `New integration`
- Pick out the workspace you want this project to have access to
- Select Internal on the type of integration (To avoid additional steps)
- Allow all capabilities for this app
- Copy the token into the `.env` file and assign it to the variable: `CLIENT_SECRET`
- Go into the Notion page you want as the parent note page
- Click the 3 dots  
  <img src="images/3dots.png" alt="3dots" width="175"/>
- Scroll down to the bottom, until you see connect to  
  <img src="images/connect.png" alt="connect" width="175"/>
- Hover over connect to and click the app you want to connect and press confirm
- Now find your URL and find the ID of the page:
- To find the ID, look at your URL and take whatever is after the name in the URL:
    - Example URL: `https://www.notion.so/Example-123456789`
    - The ID of the example URL would be `123456789`
    - Assign this ID to the `PAGE_ID` variable in the `.env` file

### 2. Connect to Obsidian
- Find the folder of your vault
- Copy the folder structure (e.g., `/Users/user/Folder/MyVault/Vault`)
- Assign the folder structure to the `VAULT_PATH` variable in the `.env` file

### 3. Running the program
- Run the program using an IDE or `python3 main.py`

## Limitations and TODO
- Limited amount of MD features
- Excalidraw file support
- Multiple vault and page support
- Deletion Support
