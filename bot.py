import logging
import asyncio
import nest_asyncio
import paramiko
import time
import re
from telegram import Update, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# Allow nested event loops (useful for VS Code, notebooks, etc.)
nest_asyncio.apply()

# Replace with your actual Telegram bot token
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

# Conversation states for /connect
CONNECT_HOST, CONNECT_PORT, CONNECT_USERNAME, CONNECT_PASSWORD = range(4)
# State for one-time command execution via /execute
EXECUTE_COMMAND = 10

# Unique custom prompt marker used to detect command completion
CUSTOM_PROMPT = "__PROMPT__"

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- /start handler: Display the main menu ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reply_keyboard = [["/connect", "/execute"], ["/exit", "/disconnect", "/help"]]
    text = (
        "*Welcome to the Telegram SSH Bot!*\n\n"
        "Once connected, the bot will be in interactive mode by default—any text you send will be executed as a command.\n"
        "Use /exit to disable interactive mode, /execute to run a one-time command, or /disconnect to end your session.\n"
        "For detailed instructions, tap /help."
    )
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )

# --- /help handler: Display usage instructions ---
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "*Usage Instructions:*\n\n"
        "• `/connect` – Establish a persistent SSH session. You'll be prompted for the hostname, port (default is 22), username, and password.\n\n"
        "• Once connected, the bot enters interactive mode by default. Every message (that does not start with a slash) is treated as a command.\n\n"
        "• `/execute` – Execute a one-time command on the SSH server.\n\n"
        "• `/exit` – Exit interactive mode. After this, you'll need to use `/execute` for commands until you re-enable interactive mode (by reconnecting).\n\n"
        "• `/disconnect` – Close the persistent SSH session.\n\n"
        "Use the menu buttons for quick access!"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# --- /connect conversation: Establish persistent SSH connection ---
async def connect_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "🔌 *Connect to SSH*\n\nEnter the SSH server hostname (e.g., `your.server.com`):",
        parse_mode=ParseMode.MARKDOWN
    )
    return CONNECT_HOST

async def connect_get_host(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["host"] = update.message.text.strip()
    await update.message.reply_text("Enter port number (default is `22`):", parse_mode=ParseMode.MARKDOWN)
    return CONNECT_PORT

async def connect_get_port(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        port = int(update.message.text.strip())
    except ValueError:
        port = 22
    context.user_data["port"] = port
    await update.message.reply_text("Enter SSH username:", parse_mode=ParseMode.MARKDOWN)
    return CONNECT_USERNAME

async def connect_get_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["username"] = update.message.text.strip()
    await update.message.reply_text("Enter SSH password:", parse_mode=ParseMode.MARKDOWN)
    return CONNECT_PASSWORD

async def connect_get_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["password"] = update.message.text.strip()
    await update.message.reply_text("Connecting to the SSH server, please wait...")
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        create_ssh_connection,
        context.user_data["host"],
        context.user_data["port"],
        context.user_data["username"],
        context.user_data["password"]
    )
    if isinstance(result, paramiko.SSHClient):
        shell = result.invoke_shell()
        context.user_data["ssh_client"] = result
        context.user_data["ssh_shell"] = shell
        # Set a custom prompt for detecting command completion.
        shell.send(f'export PS1="{CUSTOM_PROMPT} "\n')
        time.sleep(0.5)
        # Clear any initial banner or output.
        if shell.recv_ready():
            shell.recv(4096)
        # Enable interactive mode by default.
        context.user_data["interactive_mode"] = True
        await update.message.reply_text(
            "✅ *Connected successfully!* Your session is now persistent.\n"
            "Interactive mode is enabled: send any text (that doesn't start with a slash) to execute commands.\n"
            "Use `/exit` to disable interactive mode.",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(f"❌ *Failed to connect:* {result}", parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END

def create_ssh_connection(host: str, port: int, username: str, password: str):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=host, port=port, username=username, password=password)
        return client
    except Exception as e:
        logger.error(f"SSH connection failed: {e}")
        return str(e)

# --- /execute conversation: Execute a single command ---
async def execute_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if "ssh_shell" not in context.user_data:
        await update.message.reply_text("⚠️ No active SSH connection. Please use /connect first.")
        return ConversationHandler.END
    await update.message.reply_text("💻 *Execute Command*\n\nEnter the command you want to run on the server:", parse_mode=ParseMode.MARKDOWN)
    return EXECUTE_COMMAND

async def execute_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    command = update.message.text.strip()
    shell = context.user_data.get("ssh_shell")
    if not shell:
        await update.message.reply_text("⚠️ No active SSH connection. Please use /connect first.")
        return ConversationHandler.END
    await update.message.reply_text("⏳ Executing your command, please wait...")
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, run_command_on_shell, shell, command)
    await update.message.reply_text(f"*Command output:*\n```\n{result}\n```", parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END

# --- /exit command: Disable interactive mode ---
async def exit_interactive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get("interactive_mode"):
        context.user_data["interactive_mode"] = False
        await update.message.reply_text("Interactive mode disabled. Use /execute to run single commands.")
    else:
        await update.message.reply_text("Interactive mode is not enabled.")

# --- Default handler: Process messages as commands in interactive mode ---
async def interactive_mode_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get("interactive_mode") and "ssh_shell" in context.user_data:
        command = update.message.text.strip()
        # Ignore empty messages
        if not command:
            return
        # You might want to avoid executing certain texts (like greetings)
        await update.message.reply_text("⏳ Executing your command, please wait...")
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, run_command_on_shell, context.user_data["ssh_shell"], command)
        await update.message.reply_text(f"*Output:*\n```\n{result}\n```", parse_mode=ParseMode.MARKDOWN)

# --- Helper function: Execute command on the shell and capture output ---
def run_command_on_shell(shell, command: str) -> str:
    try:
        shell.send(command + "\n")
        buffer = ""
        timeout = 10  # seconds timeout for command completion
        start_time = time.time()
        while True:
            if shell.recv_ready():
                buffer += shell.recv(4096).decode("utf-8", errors="ignore")
                if CUSTOM_PROMPT in buffer:
                    break
            if time.time() - start_time > timeout:
                break
            time.sleep(0.1)
        # Remove ANSI escape sequences.
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        clean_output = ansi_escape.sub('', buffer)
        lines = clean_output.splitlines()
        if lines and command in lines[0]:
            lines.pop(0)
        lines = [line for line in lines if CUSTOM_PROMPT not in line]
        return "\n".join(lines).strip()
    except Exception as e:
        return f"Exception occurred: {e}"

# --- /disconnect command: Close the SSH session ---
async def disconnect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ssh_client = context.user_data.pop("ssh_client", None)
    ssh_shell = context.user_data.pop("ssh_shell", None)
    # Also disable interactive mode if enabled.
    context.user_data["interactive_mode"] = False
    if ssh_shell:
        ssh_shell.close()
    if ssh_client:
        ssh_client.close()
        await update.message.reply_text("🔌 SSH connection closed.")
    else:
        await update.message.reply_text("⚠️ No active SSH connection to disconnect.")

# --- /cancel for conversations ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Operation cancelled.")
    return ConversationHandler.END

# --- Main function: Set up handlers and run the bot ---
async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    connect_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("connect", connect_start)],
        states={
            CONNECT_HOST: [MessageHandler(filters.TEXT & ~filters.COMMAND, connect_get_host)],
            CONNECT_PORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, connect_get_port)],
            CONNECT_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, connect_get_username)],
            CONNECT_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, connect_get_password)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    execute_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("execute", execute_start)],
        states={
            EXECUTE_COMMAND: [MessageHandler(filters.TEXT & ~filters.COMMAND, execute_command)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(connect_conv_handler)
    application.add_handler(execute_conv_handler)
    application.add_handler(CommandHandler("exit", exit_interactive))
    application.add_handler(CommandHandler("disconnect", disconnect))
    # Default message handler for interactive mode (catches any text that is not a command)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, interactive_mode_handler))

    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
