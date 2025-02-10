# Telegram SSH Bot

<a href="https://ibb.co/Y7C3jDN3">
  <img src="https://i.ibb.co/PZLNCTrN/Rec-0026.gif" alt="Rec-0026" width="600">
</a>


A **Telegram Bot** that provides a persistent SSH session, enabling you to connect to a remote server, execute commands interactively, and receive clean output—all directly through Telegram. This project uses asynchronous programming with [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) (v20+), [Paramiko](https://www.paramiko.org/) for SSH connections, and [nest_asyncio](https://github.com/erdewit/nest_asyncio) for nested event loop compatibility.

## Features

- **Persistent SSH Session:**  
  Establish and maintain an interactive SSH session with a remote server.

- **Interactive Command Execution:**  
  Send commands through Telegram and receive output with ANSI escape sequences and login banners removed.

- **User-Friendly Interface:**  
  Enjoy a clean UI with Markdown formatting and reply keyboards for easy navigation.
  
- **Asynchronous Operation:**  
  Built with asyncio to ensure a responsive experience.

## Prerequisites

- **Python 3.7+**

- **Required Packages:**
  - [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
  - [Paramiko](https://www.paramiko.org/)
  - [nest_asyncio](https://github.com/erdewit/nest_asyncio)

## Installation & Setup

### 1. Clone the Repository

Open your terminal and clone the repository:

```bash
git clone https://github.com/cnaworld/telegram-ssh-bot.git
cd telegram-ssh-bot
```

### 2. Create and Activate a Virtual Environment

It is recommended to use a virtual environment to manage dependencies:

- **On macOS/Linux:**

  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

- **On Windows:**

  ```bash
  python -m venv venv
  venv\Scripts\activate
  ```

### 3. Install Dependencies

Install the required packages using pip:

```bash
pip install python-telegram-bot paramiko nest_asyncio
```

Alternatively, if a `requirements.txt` file is provided, run:

```bash
pip install -r requirements.txt
```

### 4. Configure the Bot Token

Open `bot.py` and replace the placeholder token:

```python
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
```

Obtain your bot token from [BotFather](https://core.telegram.org/bots#botfather).

### 5. Run the Bot

Run the bot using:

```bash
python bot.py
```

## Usage

1. **Start the Bot in Telegram:**

   Open Telegram and start a chat with your bot. Type or tap `/start` to view the main menu.

2. **Connect to an SSH Server:**

   - Tap `/connect` and follow the prompts to enter:
     - SSH server hostname (e.g., `your.server.com`)
     - Port number (default is `22`)
     - SSH username
     - SSH password
   
   The bot will establish a persistent SSH session and set a custom prompt for clean output.

3. **Execute Commands:**

   - Tap `/execute`, enter your desired command (e.g., `ls`), and the bot will return the cleaned output.

4. **Disconnect:**

   - Tap `/disconnect` to close the persistent SSH session.

5. **Help:**

   - Use `/help` to view usage instructions.

## Example Output

When you execute a command like `ls`, the bot returns output similar to:

```
Command output:
banner.txt
bot
cert.pem
dashboard_monitor.py
key.pem
venv
```

