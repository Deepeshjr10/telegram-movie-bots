from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
import os
import ssl
import certifi
import asyncio
from db_helper import DatabaseHelper
import requests
import logging
import re
from datetime import datetime, timedelta
from collections import defaultdict
import httpx
import random
import socket
from contextlib import closing
import signal
import sys
from keep_alive import keep_alive
keep_alive()

db = DatabaseHelper()
PORT = int(os.getenv("PORT", 8080))

TELEGRAM_TOKEN = "7852458153:AAE8DhR9kI1K7ZVEGyX7gdMdoHwFx_tfEPQ"
TMDB_API_KEY = "c3b8704a4df65146c194940351efa9a2"
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
DISCLAIMER = "⚠️ This message will be deleted in 7 minutes"

bot = Bot(token=TELEGRAM_TOKEN)

AVAILABLE_MOVIES = {
    'Marco': {
        'download': {
            '720p': 'https://adrinolinks.com/eZ1PT',
            '480p': 'https://adrinolinks.com/Nuws',
            '1080p': 'https://adrinolinks.com/Tq5w50'
        },
        'stream': {
            '720p': 'https://adrinolinks.com/qzGc',
            '480p': '1080https://adrinolinks.com/qzGc',
            '1080p': 'https://adrinolinks.com/qzGc'
        }
    },
    'culpa mia': {
        'download': {
            '720p': 'https://adrinolinks.com/HHBekOde',
            '480p': 'https://adrinolinks.com/yVWc54QX',
            '1080p': 'https://adrinolinks.com/4Qzi'
        },
        'stream': {
            '720p': 'not available yet',
            '480p': 'not available yet',
            '1080p': 'not available yet'

        }
    },
    'mufasa': {
        'download': {
            '480p': 'https://adrinolinks.com/S6Im1a0c',
            '720p': 'https://adrinolinks.com/PSHa09',
            '1080p': 'not available yet'
        },
        'stream': {
            '720p': 'not available yet',
            '480p': 'not available yet',
            '1080p': 'not available yet'
        }
    },
    'Your fault': {
        'download': {
            '720p': '-https://adrinolinks.com/Fh3fEN ',
            '480p': 'https://adrinolinks.com/4jmlX  ',
            '1080p': 'not available yet'

        },
        'stream': {
            '720p': 'not available yet',
            '480p': 'not available yet',
            '1080p': 'not available yet'
        },

    },

    'baby john': {
        'download': {
            '720p': 'https://adrinolinks.com/98NIvL ',
            '480p': 'https://adrinolinks.com/cKjzwa',
            '1080p': 'https://adrinolinks.com/GxMP02'

        },
        'stream': {
            '720p': 'https://adrinolinks.com/1pS1C',
            '480p': 'https://adrinolinks.com/1pS1C',
            '1080p': 'https://adrinolinks.com/1pS1C'
        },

    },

}
AVAILABLE_TV_SHOWS = {
    'squid game': {
        'episodes': {
            '1': 'https://adrinolinks.com/OIGEFWqh',
            '2': 'https://adrinolinks.com/4MT3lf4u ',
            '3': 'https://adrinolinks.com/q90vts7R ',
            '4': 'https://adrinolinks.com/9wVFSH ',
            '5': 'https://adrinolinks.com/PyfniN',
            '6': 'https://adrinolinks.com/VZ6CI '
        }
    },

}

last_activity = {}


async def check_inactivity(context: ContextTypes.DEFAULT_TYPE):
    """Check for inactive users and send them personalized messages"""
    current_time = datetime.now()
    inactive_threshold = timedelta(hours=50)

    logging.info(f"Running inactivity check at {current_time}")
    logging.info(f"Current active users: {len(last_activity)}")

    for user_id, last_active in list(last_activity.items()):
        try:
            if current_time - last_active > inactive_threshold:
                logging.info(f"Found inactive user: {user_id}")

                # Get user info from context
                chat_id = user_id
                try:
                    user_info = await context.bot.get_chat(chat_id)
                    user_name = user_info.first_name or "there"
                except TelegramError as e:
                    logging.error(f"Failed to get user info for {user_id}: {e}")
                    last_activity.pop(user_id, None)
                    continue

                try:
                    # Get a random movie recommendation
                    response = requests.get(
                        f"{TMDB_BASE_URL}/movie/popular",
                        params={
                            "api_key": TMDB_API_KEY,
                            "page": random.randint(1, 5)
                        },
                        timeout=10
                    )
                    response.raise_for_status()

                    movies = response.json().get('results', [])
                    if movies:
                        movie = random.choice(movies)
                        poster_path = movie.get('poster_path')
                        poster_url = f"{TMDB_IMAGE_BASE_URL}{poster_path}" if poster_path else None

                        message = (
                            f"👋 Hey *{user_name}*! We noticed you've been inactive for 5 minutes!\n\n"  # Updated message
                            f"How about checking out this movie?\n\n"
                            f"🎬 *{movie['title']}* ({movie.get('release_date', 'N/A')[:4]})\n"
                            f"⭐ Rating: {movie.get('vote_average', 'N/A')}/10\n\n"
                            f"📝 {movie.get('overview', 'No overview available.')}"
                        )

                        try:
                            if poster_url:
                                await context.bot.send_photo(
                                    chat_id=chat_id,
                                    photo=poster_url,
                                    caption=message,
                                    parse_mode=ParseMode.MARKDOWN
                                )
                            else:
                                await context.bot.send_message(
                                    chat_id=chat_id,
                                    text=message,
                                    parse_mode=ParseMode.MARKDOWN
                                )

                            # Update last activity to avoid spam
                            last_activity[user_id] = current_time
                            logging.info(f"Successfully sent inactivity message to user {user_id}")

                        except TelegramError as e:
                            logging.error(f"Failed to send message to {user_id}: {e}")
                            last_activity.pop(user_id, None)

                except (requests.RequestException, ValueError) as e:
                    logging.error(f"Error fetching movie data: {e}")
                    continue

        except Exception as e:
            logging.error(f"Error processing user {user_id}: {e}")
            continue


def create_application():
    """Create the application with proper SSL configuration"""
    # Create SSL context
    ssl_context = ssl.create_default_context(cafile=certifi.where())

    # Configure the HTTP client
    http_client = httpx.AsyncClient(
        verify=ssl_context,
        timeout=30.0
    )

    # Build application with custom client
    return (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .http_version("1.1")  # Use HTTP/1.1 for better compatibility
        .get_updates_http_version("1.1")
        .build()
    )


class BubbleManager:
    def __init__(self):
        self.active_bubbles = {}  # Store message_id for each chat_id

    async def create_bubble(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
        """Create a bubble notification"""
        # Remove existing bubble if any
        if chat_id in self.active_bubbles:
            try:
                await context.bot.delete_message(
                    chat_id=chat_id,
                    message_id=self.active_bubbles[chat_id]
                )
            except:
                pass

        keyboard = [[InlineKeyboardButton("↻ Restart Bot", callback_data="restart_bot")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            # Pin the message to make it persistent
            message = await context.bot.send_message(
                chat_id=chat_id,
                text="🤖 *Movie Bot Active*\nClick below to restart the bot",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

            try:
                # Try to pin the message
                await context.bot.pin_chat_message(
                    chat_id=chat_id,
                    message_id=message.message_id,
                    disable_notification=True
                )
            except:
                # If pinning fails, that's okay - the bubble will still work
                pass

            self.active_bubbles[chat_id] = message.message_id
            return message.message_id
        except Exception as e:
            logging.error(f"Failed to create bubble: {e}")
            return None

    async def remove_bubble(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
        """Remove the bubble notification"""
        if chat_id in self.active_bubbles:
            try:
                # Try to unpin first
                try:
                    await context.bot.unpin_chat_message(
                        chat_id=chat_id,
                        message_id=self.active_bubbles[chat_id]
                    )
                except:
                    pass

                # Then delete the message
                await context.bot.delete_message(
                    chat_id=chat_id,
                    message_id=self.active_bubbles[chat_id]
                )
                del self.active_bubbles[chat_id]
            except Exception as e:
                logging.error(f"Failed to remove bubble: {e}")


bubble_manager = BubbleManager()


async def delete_message_later(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int):
    await asyncio.sleep(300)  # 5 minutes
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logging.error(f"Failed to delete message: {e}")


async def send_auto_delete_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup=None,
                                   parse_mode=None):
    message = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode
    )
    # Schedule message deletion
    context.application.create_task(delete_message_later(context, message.chat_id, message.message_id))
    # Also delete the user's message if it exists
    if update.message:
        context.application.create_task(
            delete_message_later(context, update.message.chat_id, update.message.message_id))
    return message


def normalize_title(title):
    """Simple title normalization"""
    return title.lower().strip()


def find_matching_content(search_title):
    """Simple direct matching of titles"""
    search_title = normalize_title(search_title)

    # Check movies first
    for movie_title in AVAILABLE_MOVIES.keys():
        if normalize_title(movie_title) in search_title or search_title in normalize_title(movie_title):
            return ('movie', movie_title)

    # Then check TV shows
    for show_title in AVAILABLE_TV_SHOWS.keys():
        if normalize_title(show_title) in search_title or search_title in normalize_title(show_title):
            return ('tv_show', show_title)

    return None


async def movie_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, movie_id, title = query.data.split('_', 2)
    await update_user_activity(update.effective_user.id)

    # Get movie details from TMDB
    response = requests.get(
        f"{TMDB_BASE_URL}/movie/{movie_id}",
        params={"api_key": TMDB_API_KEY}
    )
    movie = response.json()

    # Get poster URL
    poster_url = f"{TMDB_IMAGE_BASE_URL}{movie.get('poster_path')}" if movie.get('poster_path') else None

    # Create base message
    base_message = (
        f"🎬 *{movie['title']}* ({movie.get('release_date', 'N/A')[:4]})\n"
        f"⭐ Rating: {movie.get('vote_average', 'N/A')}/10\n"
        f"📝 {movie.get('overview', 'No overview available.')}\n\n"
    )

    # Check if movie is available
    print(f"Searching for: {movie['title']}")  # Debug print
    content_match = find_matching_content(movie['title'])
    print(f"Match found: {content_match}")  # Debug print

    if content_match:
        content_type, content_title = content_match

        if content_type == 'tv_show':
            show_data = AVAILABLE_TV_SHOWS[content_title]
            download_info = "📺 *Available Episodes:*\n\n"
            for ep_num, link in show_data['episodes'].items():
                download_info += f"Episode {ep_num}: {link}\n"

        else:  # movie
            movie_data = AVAILABLE_MOVIES[content_title]
            download_info = "📥 *Download Links:*\n"

            # Add download links
            if '480p' in movie_data['download']:
                download_info += f"480p: {movie_data['download']['480p']}\n"
            if '720p' in movie_data['download']:
                download_info += f"720p: {movie_data['download']['720p']}\n"
            if '1080p' in movie_data['download']:
                download_info += f"1080p: {movie_data['download']['1080p']}\n"

            # Add streaming links
            download_info += "\n🎬 *Streaming Links:*\n"
            if '480p' in movie_data['stream']:
                download_info += f"480p: {movie_data['stream']['480p']}\n"
            if '720p' in movie_data['stream']:
                download_info += f"720p: {movie_data['stream']['720p']}\n"
            if '1080p' in movie_data['stream']:
                download_info += f"1080p: {movie_data['stream']['1080p']}\n"
    else:
        download_info = "📥 This movie is not available yet!\nContact @balaram129 for updates."

    # Combine messages
    full_message = base_message + "\n" + download_info

    # Send response
    try:
        if poster_url:
            sent_message = await query.message.reply_photo(
                photo=poster_url,
                caption=full_message,
                parse_mode='Markdown'
            )
        else:
            sent_message = await query.message.reply_text(
                text=full_message,
                parse_mode='Markdown'
            )

        # Schedule message deletion
        context.application.create_task(
            delete_message_later(context, sent_message.chat_id, sent_message.message_id)
        )

        # Try to delete the original callback message
        try:
            await query.message.delete()
        except Exception as e:
            print(f"Error deleting original message: {e}")

    except Exception as e:
        print(f"Error sending movie information: {e}")
        await query.message.reply_text(
            "❌ An error occurred while fetching movie information. Please try again."
        )

    await query.answer()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def update_user_activity(user_id):
    """Update the last activity timestamp for a user"""
    last_activity[user_id] = datetime.now()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_name = update.message.from_user.first_name
    await update_user_activity(update.effective_user.id)

    # Create bubble notification
    keyboard = [
        [
            InlineKeyboardButton("🔄 Restart Bot", callback_data="restart_bot")
        ]
    ]
    bubble_markup = InlineKeyboardMarkup(keyboard)

    try:
        bubble_msg = await context.bot.send_message(
            chat_id=chat_id,
            text="🤖 *Movie Bot Active*\nClick below to restart the bot",
            reply_markup=bubble_markup,
            parse_mode=ParseMode.MARKDOWN
        )

        # Try to pin the bubble message
        try:
            await context.bot.pin_chat_message(
                chat_id=chat_id,
                message_id=bubble_msg.message_id,
                disable_notification=True
            )
        except Exception as e:
            logging.warning(f"Could not pin bubble message: {e}")

    except Exception as e:
        logging.error(f"Failed to create bubble: {e}")

    # Send welcome message
    welcome_keyboard = [
        [
            InlineKeyboardButton("🎬 Download Movies", callback_data="search_movies"),
            InlineKeyboardButton("👨‍🦱 Search by Actor", callback_data="search_actor")
        ],
        [InlineKeyboardButton("🎲 Random Movies", callback_data="random_movies"),
         InlineKeyboardButton("📈 Popular Movies", callback_data='popular'), ]
    ]
    welcome_markup = InlineKeyboardMarkup(welcome_keyboard)

    welcome_msg = (
        f"Welcome @{user_name}!\n\n"
        "⚠️ *Note: Messages will auto-delete after 5 minutes to avoid copyright* 🖋️\n\n"
        "Choose an option below:"
    )

    try:
        message = await context.bot.send_message(
            chat_id=chat_id,
            text=welcome_msg,
            reply_markup=welcome_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        # Schedule deletion
        asyncio.create_task(delete_message_later(context, chat_id, message.message_id))
    except Exception as e:
        logging.error(f"Failed to send welcome message: {e}")


async def send_with_warning(message, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup=None, parse_mode=None):
    try:
        if hasattr(message, 'reply_text'):
            sent_message = await message.reply_text(
                f"{text}\n\n{DISCLAIMER}",
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        else:
            sent_message = await message.edit_text(
                f"{text}\n\n{DISCLAIMER}",
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )

        await delete_message_later(context, sent_message.chat_id, sent_message.message_id)
        return sent_message
    except TelegramError as e:
        print(f"Error sending message: {e}")
        return None


async def restart_bot_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bot restart from bubble"""
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    user_name = query.from_user.first_name  # Fixed: Get user from callback_query

    # Remove old bubble
    await bubble_manager.remove_bubble(context, chat_id)

    # Create new bubble notification
    keyboard = [
        [
            InlineKeyboardButton("🔄 Restart Bot", callback_data="restart_bot")
        ]
    ]
    bubble_markup = InlineKeyboardMarkup(keyboard)

    try:
        bubble_msg = await context.bot.send_message(
            chat_id=chat_id,
            text="🤖 *Movie Bot Active*\nClick below to restart the bot",
            reply_markup=bubble_markup,
            parse_mode=ParseMode.MARKDOWN
        )

        try:
            await context.bot.pin_chat_message(
                chat_id=chat_id,
                message_id=bubble_msg.message_id,
                disable_notification=True
            )
        except Exception as e:
            logging.warning(f"Could not pin bubble message: {e}")

    except Exception as e:
        logging.error(f"Failed to create bubble: {e}")

    # Send welcome message
    welcome_keyboard = [
        [
            InlineKeyboardButton("🎬 Download Movies", callback_data="search_movies"),
            InlineKeyboardButton("👨‍🦱 Search by Actor", callback_data="search_actor")
        ],
        [InlineKeyboardButton("🎲 Random Movies", callback_data="random_movies"),
         InlineKeyboardButton("📈 Popular Movies", callback_data='popular'), ]
    ]
    welcome_markup = InlineKeyboardMarkup(welcome_keyboard)

    welcome_msg = (
        f"Welcome @{user_name}!\n\n"
        "⚠️ *Note: Messages will auto-delete after 5 minutes to avoid copyright* 🖋️\n\n"
        "Choose an option below:"
    )

    try:
        message = await context.bot.send_message(
            chat_id=chat_id,
            text=welcome_msg,
            reply_markup=welcome_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        # Schedule deletion
        context.application.create_task(delete_message_later(context, chat_id, message.message_id))

        # Delete the callback query message if it exists
        if query.message:
            try:
                await query.message.delete()
            except Exception as e:
                logging.error(f"Failed to delete callback query message: {e}")

    except Exception as e:
        logging.error(f"Failed to send welcome message: {e}")


async def get_popular_movies(message, context: ContextTypes.DEFAULT_TYPE):
    try:
        url = f"{TMDB_BASE_URL}/movie/popular"
        params = {
            "api_key": TMDB_API_KEY,
            "language": "en-US",
            "page": 1
        }

        response = requests.get(url, params=params)
        response.raise_for_status()

        movies = response.json().get("results", [])[:5]

        response_text = "🎬 Currently Popular Movies:\n\n"
        keyboard = []  # Create keyboard for movie buttons

        for i, movie in enumerate(movies, 1):
            response_text += f"{i}. *{movie['title']}* ({movie.get('release_date', '')[:4]})\n"
            response_text += f"Rating: ⭐ {movie.get('vote_average', 'N/A')}/10\n\n"

            # Add button for each movie
            callback_data = f"movie_{movie['id']}_{movie['title']}"
            if len(callback_data) > 64:  # Telegram callback data limit
                callback_data = callback_data[:64]
            keyboard.append([InlineKeyboardButton(f"🎬 {movie['title']}", callback_data=callback_data)])

        # Add refresh button at the bottom
        keyboard.append([InlineKeyboardButton("🔄 Refresh Popular Movies", callback_data='popular')])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await send_with_warning(message, context, response_text, reply_markup=reply_markup, parse_mode='Markdown')

    except Exception as e:
        print(f"Error fetching popular movies: {e}")
        keyboard = [[InlineKeyboardButton("🔄 Try Again", callback_data='popular')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await send_with_warning(message, context,
                                "Sorry, couldn't fetch popular movies right now.",
                                reply_markup=reply_markup)


# Update the popular_movies_callback function to handle the loading state better
async def popular_movies_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle popular movies button click"""
    query = update.callback_query
    await query.answer()

    try:
        # Send loading animation while fetching new movies
        loading_message = await send_loading_gif(context, query.message.chat_id)

        # Get the popular movies data
        url = f"{TMDB_BASE_URL}/movie/popular"
        params = {
            "api_key": TMDB_API_KEY,
            "language": "en-US",
            "page": random.randint(1, 5)  # Add some randomness to refresh
        }

        response = requests.get(url, params=params)
        response.raise_for_status()

        movies = response.json().get("results", [])[:5]

        response_text = "🎬 Currently Popular Movies:\n\n"
        keyboard = []

        for i, movie in enumerate(movies, 1):
            response_text += f"{i}. *{movie['title']}* ({movie.get('release_date', '')[:4]})\n"
            response_text += f"Rating: ⭐ {movie.get('vote_average', 'N/A')}/10\n\n"

            callback_data = f"movie_{movie['id']}_{movie['title']}"
            if len(callback_data) > 64:
                callback_data = callback_data[:64]
            keyboard.append([InlineKeyboardButton(f"🎬 {movie['title']}", callback_data=callback_data)])

        # Add refresh button at the bottom
        keyboard.append([InlineKeyboardButton("🔄 Refresh Popular Movies", callback_data='popular')])

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Delete loading message if it exists
        if loading_message:
            try:
                await loading_message.delete()
            except Exception as e:
                logging.error(f"Error deleting loading message: {e}")

        # Send new message with updated movies
        new_message = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"{response_text}\n\n{DISCLAIMER}",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

        # Schedule deletion for the new message
        context.application.create_task(
            delete_message_later(context, new_message.chat_id, new_message.message_id)
        )

        # Delete the original message that contained the refresh button
        try:
            await query.message.delete()
        except Exception as e:
            logging.error(f"Error deleting original message: {e}")

    except Exception as e:
        logging.error(f"Error in popular movies callback: {e}")

        # Delete loading message if it exists
        if loading_message:
            try:
                await loading_message.delete()
            except Exception as e:
                logging.error(f"Error deleting loading message: {e}")

        # Send error message
        error_message = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="❌ An error occurred while refreshing movies. Please try again.\n\n" + DISCLAIMER,
            parse_mode=ParseMode.MARKDOWN
        )

        # Schedule deletion for error message
        context.application.create_task(
            delete_message_later(context, error_message.chat_id, error_message.message_id)
        )


async def send_loading_gif(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Send a loading GIF message and return the message object"""
    try:
        # You can replace this URL with any other loading GIF you prefer
        loading_gif_url = "https://media.tenor.com/iCqG_iT-h48AAAAM/bills-ugh.gif"
        message = await context.bot.send_animation(
            chat_id=chat_id,
            animation=loading_gif_url,
            caption="🔍 *Searching for movies...*",
            parse_mode=ParseMode.MARKDOWN
        )
        return message
    except Exception as e:
        logging.error(f"Error sending loading GIF: {e}")
        return None


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stop command"""
    chat_id = update.effective_chat.id
    user = update.message.from_user

    try:
        # Remove the bubble message if it exists
        await bubble_manager.remove_bubble(context, chat_id)

        # Send stop confirmation message
        message = await context.bot.send_message(
            chat_id=chat_id,
            text=f"Goodbye {user.first_name}! Bot stopped. Use /start to restart.",
            parse_mode=ParseMode.MARKDOWN
        )

        # Schedule message deletion after 5 minutes
        context.application.create_task(
            delete_message_later(context, chat_id, message.message_id)
        )

        # Also delete the user's command message
        if update.message:
            context.application.create_task(
                delete_message_later(context, chat_id, update.message.message_id)
            )

    except Exception as e:
        logging.error(f"Error in stop command: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Error stopping the bot. Please try again."
        )


async def search_movies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search movies with loading animation"""
    query = update.message.text.lower().strip()
    user = update.message.from_user
    await update_user_activity(update.effective_user.id)

    # Send loading animation
    loading_message = await send_loading_gif(context, update.message.chat_id)

    # Log the search
    db.log_search(
        user_id=user.id,
        username=user.username or f"user_{user.id}",
        query=query
    )

    try:
        # Get TMDB results
        response = requests.get(
            f"{TMDB_BASE_URL}/search/movie",
            params={
                "api_key": TMDB_API_KEY,
                "query": query
            }
        )

        results = response.json().get('results', [])[:5]  # Get top 5 TMDB results

        # Delete loading message
        if loading_message:
            try:
                await loading_message.delete()
            except Exception as e:
                logging.error(f"Error deleting loading message: {e}")

        keyboard = []

        # Add Beast Games entry if the search includes "beast"
        if "beast" in query:
            # Add custom Beast Games (2024) entry at the top
            keyboard.append([
                InlineKeyboardButton(
                    "Beast Games (2024) - Special Content",
                    callback_data="custom_beast_games_2024"
                )
            ])

        # Add TMDB results
        for movie in results:
            callback_data = f"movie_{movie['id']}_{movie['title']}"
            if len(callback_data) > 64:
                callback_data = callback_data[:64]
            keyboard.append([
                InlineKeyboardButton(
                    f"{movie['title']} ({movie.get('release_date', 'N/A')[:4]})",
                    callback_data=callback_data
                )
            ])

        if not keyboard:
            message = await update.message.reply_text(
                "❌ No movies found. Please try another search.",
                parse_mode=ParseMode.MARKDOWN
            )
            context.application.create_task(
                delete_message_later(context, message.chat_id, message.message_id)
            )
            return

        reply_markup = InlineKeyboardMarkup(keyboard)
        message = await update.message.reply_text(
            "🎬 *Select a movie:*",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

        # Schedule message deletion
        context.application.create_task(
            delete_message_later(context, message.chat_id, message.message_id)
        )



    except Exception as e:
        logging.error(f"Error searching movies: {e}")
        if loading_message:
            try:
                await loading_message.delete()
            except Exception as e:
                logging.error(f"Error deleting loading message: {e}")

        message = await update.message.reply_text(
            "❌ An error occurred while searching. Please try again.",
            parse_mode=ParseMode.MARKDOWN
        )
        context.application.create_task(
            delete_message_later(context, message.chat_id, message.message_id)
        )

    # Delete user's search message
    try:
        await update.message.delete()
    except Exception as e:
        logging.error(f"Error deleting user message: {e}")


async def custom_beast_games_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        base_message = "🎮 *Beast Games (2024)*\n\n"
        episodes_info = "*Available Episodes:*\n"
        episodes_info += "Episode 1: example.com\n"
        episodes_info += "Episode 2: example.4567\n"
        episodes_info += "Episode 3: sdfghj.89.co\n"

        # Send message with image and episode links
        message = await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo="https://m.media-amazon.com/images/M/MV5BYzA3MDFkMTQtNTk0My00MDA3LTkxNDUtZjVhNzYzMGI2N2YwXkEyXkFqcGc@._V1_.jpg",
            caption=f"{base_message}{episodes_info}\n\n{DISCLAIMER}",
            parse_mode=ParseMode.MARKDOWN
        )

        # Schedule message deletion
        context.application.create_task(
            delete_message_later(context, message.chat_id, message.message_id)
        )

        # Delete the original message with buttons
        try:
            await query.message.delete()
        except Exception as e:
            logging.error(f"Error deleting original message: {e}")

    except Exception as e:
        logging.error(f"Error sending Beast Games info: {e}")
        message = await query.message.reply_text(
            "❌ An error occurred. Please try again.",
            parse_mode=ParseMode.MARKDOWN
        )
        context.application.create_task(
            delete_message_later(context, message.chat_id, message.message_id)
        )


async def search_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    user = update.message.from_user

    if context.user_data.get('searching_actor'):
        await search_actor(update, context)
        context.user_data['searching_actor'] = False
        return

    await search_movies(update, context)


async def search_actor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    user = update.message.from_user

    db.log_search(
        user_id=user.id,
        username=user.username or f"user_{user.id}",
        query=query,
        is_actor=True  # Set the flag for actor searches
    )
    response = requests.get(
        f"{TMDB_BASE_URL}/search/person",
        params={
            "api_key": TMDB_API_KEY,
            "query": query
        }
    )

    results = response.json().get('results', [])[:5]
    if not results:
        await update.message.reply_text("No actors found. Try another search.")
        return

    keyboard = []
    for actor in results:
        callback_data = f"actor_{actor['id']}_{actor['name']}"
        if len(callback_data) > 64:
            callback_data = callback_data[:64]
        keyboard.append([InlineKeyboardButton(actor['name'], callback_data=callback_data)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select an actor:", reply_markup=reply_markup)


async def get_random_movies(api_key: str, count: int = 6):
    """Fetch random popular movies from TMDB"""
    try:
        # Get a list of popular movies first
        response = requests.get(
            f"{TMDB_BASE_URL}/movie/popular",
            params={
                "api_key": api_key,
                "page": random.randint(1, 5)  # Get a random page of popular movies
            }
        )

        if response.status_code != 200:
            return []

        movies = response.json().get('results', [])
        # Shuffle and return requested number of movies
        random.shuffle(movies)
        return movies[:count]
    except Exception as e:
        logging.error(f"Error fetching random movies: {e}")
        return []


async def random_movies_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle random movies button click"""
    query = update.callback_query
    await query.answer()

    try:
        # Get random movies
        movies = await get_random_movies(TMDB_API_KEY)

        if not movies:
            message = await query.message.reply_text(
                "❌ Sorry, couldn't fetch random movies. Please try again."
            )
            context.application.create_task(
                delete_message_later(context, message.chat_id, message.message_id)
            )
            return

        # Create keyboard with movie buttons
        keyboard = []
        for movie in movies:
            callback_data = f"movie_{movie['id']}_{movie['title']}"
            if len(callback_data) > 64:
                callback_data = callback_data[:64]
            keyboard.append([
                InlineKeyboardButton(
                    f"🎬 {movie['title']} ({movie.get('release_date', 'N/A')[:4]})",
                    callback_data=callback_data
                )
            ])

        # Add a refresh button at the bottom
        keyboard.append([
            InlineKeyboardButton("🔄 Get More Random Movies", callback_data="random_movies")
        ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send message with random movies
        message = await query.message.reply_text(
            "🎲 Here are some random movies you might like:",
            reply_markup=reply_markup
        )

        # Schedule message deletion
        context.application.create_task(
            delete_message_later(context, message.chat_id, message.message_id)
        )

        # Try to delete the original message
        try:
            await query.message.delete()
        except Exception as e:
            logging.error(f"Error deleting original message: {e}")

    except Exception as e:
        logging.error(f"Error in random movies callback: {e}")
        message = await query.message.reply_text(
            "❌ An error occurred. Please try again."
        )
        context.application.create_task(
            delete_message_later(context, message.chat_id, message.message_id)
        )


async def actor_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, actor_id, name = query.data.split('_', 2)
    await update_user_activity(update.effective_user.id)

    user = query.from_user
    db.log_search(
        user_id=user.id,
        username=user.username or f"user_{user.id}",
        query=f"Selected actor: {name}",
        is_actor=True  # Set the flag for actor selections
    )

    response = requests.get(
        f"{TMDB_BASE_URL}/person/{actor_id}/movie_credits",
        params={"api_key": TMDB_API_KEY}
    )

    movies = response.json().get('cast', [])[:5]
    keyboard = []
    for movie in movies:
        callback_data = f"movie_{movie['id']}_{movie['title']}"
        if len(callback_data) > 64:
            callback_data = callback_data[:64]
        keyboard.append([InlineKeyboardButton(f"{movie['title']} ({movie.get('release_date', 'N/A')[:4]})",
                                              callback_data=callback_data)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    message = await query.message.reply_text(f"Movies starring {name}:", reply_markup=reply_markup)
    asyncio.create_task(delete_message_later(context, message.chat_id, message.message_id))


async def handle_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks with loading animation"""
    query = update.callback_query
    await query.answer()
    await update_user_activity(update.effective_user.id)

    if query.data == "search_movies":
        # Send loading GIF first
        loading_message = await send_loading_gif(context, query.message.chat_id)

        # Wait for a short time to show the loading animation (optional)
        await asyncio.sleep(2)

        # Send the actual search prompt
        message = await query.message.reply_text(
            "🎬 Please send me a movie title to search.",
            parse_mode=ParseMode.MARKDOWN
        )

        # Delete the loading GIF
        if loading_message:
            try:
                await loading_message.delete()
            except Exception as e:
                logging.error(f"Error deleting loading message: {e}")

        # Schedule deletion of the prompt message
        context.application.create_task(
            delete_message_later(context, message.chat_id, message.message_id)
        )

    elif query.data == "search_actor":
        message = await query.message.reply_text(
            "👨‍🦱 Please send me an actor name to search.",
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data['searching_actor'] = True
        context.application.create_task(
            delete_message_later(context, message.chat_id, message.message_id)
        )

    # Try to delete the original message that contained the button
    try:
        await query.message.delete()
    except Exception as e:
        logging.error(f"Error deleting original message: {e}")


def signal_handler(signum, frame):
    """Handle interrupt signals gracefully"""
    print("\nReceived interrupt signal. Cleaning up...")
    sys.exit(0)


def main():
    # Set up logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger = logging.getLogger(__name__)

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Create the application
        app = create_application()

        # Add handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("stop", stop_command))
        app.add_handler(CallbackQueryHandler(restart_bot_callback, pattern="^restart_bot$"))
        app.add_handler(CallbackQueryHandler(handle_button_callback, pattern="^(search_movies|search_actor)$"))
        app.add_handler(CallbackQueryHandler(random_movies_callback, pattern="^random_movies$"))
        app.add_handler(CallbackQueryHandler(popular_movies_callback, pattern="^popular$"))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_query))
        app.add_handler(CallbackQueryHandler(actor_callback, pattern="^actor_"))
        app.add_handler(CallbackQueryHandler(movie_callback, pattern="^movie_"))
        app.add_handler(CallbackQueryHandler(custom_beast_games_callback, pattern="^custom_beast_games_2024$"))

        # Set up job queue
        job_queue = app.job_queue
        job_queue.run_repeating(check_inactivity, interval=timedelta(hours=6), first=10)

        logger.info("Starting bot with 5-minute inactivity check...")
        logger.info(f"Starting bot on port {PORT}...")

        # Run the bot with the event loop
        app.run_polling(allowed_updates=Update.ALL_TYPES, close_loop=False)

        from http.server import HTTPServer, BaseHTTPRequestHandler

        class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'Bot is running')

        def run_server():
            server = HTTPServer(('0.0.0.0', PORT), SimpleHTTPRequestHandler)
            logger.info(f'Starting web server on port {PORT}')
            server.serve_forever()

        # Start the web server in a separate thread
        import threading
        server_thread = threading.Thread(target=run_server)
        server_thread.daemon = True
        server_thread.start()

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Shutting down...")
        if 'loop' in locals():
            loop.close()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        if 'loop' in locals():
            loop.close()
        sys.exit(1)
    finally:
        # Ensure the loop is closed
        if 'loop' in locals():
            if loop.is_running():
                loop.stop()
            if not loop.is_closed():
                loop.close()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nBot stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError occurred: {e}")
        sys.exit(1)
