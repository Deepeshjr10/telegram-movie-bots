# db_helper.py
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime, timedelta
import threading
import time
import os
import logging
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler

TOKEN = "7852458153:AAE8DhR9kI1K7ZVEGyX7gdMdoHwFx_tfEPQ"

# Create the Flask app
app = Flask(__name__)

# Initialize the bot and the application
bot = Bot(TOKEN)
application = Application.builder().token(TOKEN).build()

# Command handler
async def start(update: Update, context):
    await update.message.reply_text("Hello! Welcome to the bot.")

application.add_handler(CommandHandler("start", start))

# Define the webhook route
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()
    update = Update.de_json(data, bot)
    application.update_queue.put_nowait(update)
    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='search_analytics.log'
)


class DatabaseHelper:
    def __init__(self, db_name='search_analytics.db'):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()

                # Check if table exists
                cursor.execute('''
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='user_searches'
                ''')
                table_exists = cursor.fetchone()

                if not table_exists:
                    # Create new table with all columns
                    cursor.execute('''
                        CREATE TABLE user_searches (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            username TEXT,
                            query TEXT NOT NULL,
                            platform TEXT,
                            search_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            is_actor BOOLEAN DEFAULT 0
                        )
                    ''')
                else:
                    # Check if is_actor column exists
                    cursor.execute('PRAGMA table_info(user_searches)')
                    columns = [col[1] for col in cursor.fetchall()]

                    if 'is_actor' not in columns:
                        # Add is_actor column if it doesn't exist
                        cursor.execute('''
                            ALTER TABLE user_searches 
                            ADD COLUMN is_actor BOOLEAN DEFAULT 0
                        ''')

                # Create indexes for better performance
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_user_id 
                    ON user_searches(user_id)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_search_time 
                    ON user_searches(search_time)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_is_actor 
                    ON user_searches(is_actor)
                ''')

                conn.commit()
                logging.info("Database initialized successfully")
        except Exception as e:
            logging.error(f"Error initializing database: {e}")
            raise

    def log_search(self, user_id, username, query, platform='telegram', is_actor=False):
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO user_searches (user_id, username, query, platform, search_time, is_actor)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, username, query, platform, datetime.now(), is_actor))
                conn.commit()
                logging.info(f"Search logged - User: {username}, Query: {query}, Is Actor: {is_actor}")
        except Exception as e:
            logging.error(f"Error logging search: {e}")
            raise


class SearchAnalyticsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Search Analytics Dashboard")

        # Make window full screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"{screen_width}x{screen_height}+0+0")

        # Configure window to use available space
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.db = DatabaseHelper()

        # Configure style
        self.setup_style()

        # Create main container
        self.create_main_layout()

        # Initialize update thread
        self.should_update = True
        self.update_thread = threading.Thread(target=self.update_loop, daemon=True)
        self.update_thread.start()



    def setup_style(self):
        style = ttk.Style()
        style.theme_use('clam')

        # Configure colors and styles
        style.configure('Stats.TLabel', padding=5, font=('Helvetica', 10))
        style.configure('Header.TLabel', font=('Helvetica', 12, 'bold'))
        style.configure('Title.TLabel', font=('Helvetica', 14, 'bold'))

    def create_main_layout(self):
        # Main container
        main_container = ttk.Frame(self.root, padding="10")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Create all widgets
        self.create_header(main_container)
        self.create_statistics_frame(main_container)
        self.create_search_notebook(main_container)
        self.create_recent_searches_frame(main_container)

        # Configure weights
        self.configure_grid_weights(main_container)

    def create_header(self, parent):
        header_frame = ttk.Frame(parent)
        header_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # Title on the left
        title_label = ttk.Label(header_frame, text="Search Analytics Dashboard", style='Title.TLabel')
        title_label.pack(side=tk.LEFT)

        # Button frame on the right
        button_frame = ttk.Frame(header_frame)
        button_frame.pack(side=tk.RIGHT)

        # Share button
        share_btn = ttk.Button(button_frame, text="Share Report", command=self.share_report)
        share_btn.pack(side=tk.RIGHT, padx=5)

        # Show Folder button
        folder_btn = ttk.Button(button_frame, text="Show Reports Folder", command=self.open_reports_folder)
        folder_btn.pack(side=tk.RIGHT, padx=5)

        # Refresh button
        refresh_btn = ttk.Button(button_frame, text="Refresh Data", command=self.refresh_data)
        refresh_btn.pack(side=tk.RIGHT, padx=5)

    def open_reports_folder(self):
        try:
            # Get the directory where reports are saved
            current_dir = os.path.abspath(os.path.dirname(__file__))

            # Open the folder in file explorer
            if os.name == 'nt':  # Windows
                os.startfile(current_dir)
            elif os.name == 'posix':  # macOS and Linux
                subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', current_dir])

        except Exception as e:
            logging.error(f"Error opening reports folder: {e}")
            messagebox.showerror("Error", "Failed to open reports folder")

    def share_report(self):
        try:
            # Generate report content
            report = self.generate_report()

            # Create temporary file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"search_analytics_report_{timestamp}.txt"

            # Get the absolute path
            file_path = os.path.abspath(filename)

            with open(file_path, "w", encoding='utf-8') as f:
                f.write(report)

            # Open file with default system application
            if os.name == 'nt':  # Windows
                os.startfile(file_path)
            elif os.name == 'posix':  # macOS and Linux
                import subprocess
                subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', file_path])

            # Show success message with file location
            messagebox.showinfo("Report Generated",
                                f"Report has been saved and opened from:\n{file_path}")

        except Exception as e:
            logging.error(f"Error generating report: {e}")
            messagebox.showerror("Error", "Failed to generate report")

    def generate_report(self):
        report = []

        # Add header
        report.append("Search Analytics Dashboard Report")
        report.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Add statistics
        report.append("Statistics:")
        for var in self.stats_vars.values():
            report.append(var.get())
        report.append("")

        # Add top searches
        report.append("Top Searches Today:")
        for item in self.trees['today'].get_children():
            values = self.trees['today'].item(item)['values']
            report.append(f"{values[0]}. {values[1]} - {values[2]} searches")
        report.append("")

        # Add recent searches
        report.append("Recent Searches:")
        for item in self.searches_tree.get_children()[:20]:  # Last 20 searches
            values = self.searches_tree.item(item)['values']
            report.append(f"Time: {values[0]}, User: {values[2]}, Query: {values[3]}, Type: {values[5]}")

        return "\n".join(report)

    def create_statistics_frame(self, parent):
        stats_frame = ttk.LabelFrame(parent, text="Statistics", padding="5")
        stats_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        # Statistics variables
        self.stats_vars = {
            'total_users': tk.StringVar(value="Total Users: 0"),
            'daily_users': tk.StringVar(value="Today's Users: 0"),
            'total_searches': tk.StringVar(value="Total Searches: 0"),
            'actor_searches': tk.StringVar(value="Actor Searches: 0"),
            'today_searches': tk.StringVar(value="Today's Searches: 0")
        }

        # Create labels for each statistic
        col = 0
        for var in self.stats_vars.values():
            ttk.Label(stats_frame, textvariable=var, style='Stats.TLabel').grid(
                row=0, column=col, padx=10)
            col += 1

    def create_search_notebook(self, parent):
        # Create notebook for different search views
        self.notebook = ttk.Notebook(parent)
        self.notebook.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

        # Create frames for each tab
        self.create_general_searches_tab()
        self.create_actors_tab()
        self.create_trends_tab()

    def create_general_searches_tab(self):
        general_frame = ttk.Frame(self.notebook)
        self.notebook.add(general_frame, text="General Searches")

        # Time period notebook
        self.time_notebook = ttk.Notebook(general_frame)
        self.time_notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Create trees for different time periods
        self.trees = {
            'today': self.create_search_tree("Today"),
            'yesterday': self.create_search_tree("Yesterday"),
            'week': self.create_search_tree("This Week"),
            'month': self.create_search_tree("This Month"),
            'year': self.create_search_tree("This Year")
        }

    def create_actors_tab(self):
        actors_frame = ttk.Frame(self.notebook)
        self.notebook.add(actors_frame, text="Top Actors")

        # Create actors tree
        self.actors_tree = self.create_actors_tree(actors_frame)

        # Create control panel
        self.create_actors_control_panel(actors_frame)

    def create_actors_control_panel(self, parent):
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=1, column=0, pady=5, sticky=(tk.W, tk.E))

        # Limit selector
        ttk.Label(control_frame, text="Show top:").pack(side=tk.LEFT, padx=5)
        self.limit_var = tk.StringVar(value="10")
        limit_combo = ttk.Combobox(control_frame, textvariable=self.limit_var,
                                   values=["10", "20", "50", "100"], width=5)
        limit_combo.pack(side=tk.LEFT)

        # Time period selector
        ttk.Label(control_frame, text="Time period:").pack(side=tk.LEFT, padx=(20, 5))
        self.period_var = tk.StringVar(value="All Time")
        period_combo = ttk.Combobox(control_frame, textvariable=self.period_var,
                                    values=["All Time", "Today", "This Week", "This Month", "This Year"],
                                    width=10)
        period_combo.pack(side=tk.LEFT)

        # Bind events
        limit_combo.bind('<<ComboboxSelected>>', lambda e: self.update_actors_tree())
        period_combo.bind('<<ComboboxSelected>>', lambda e: self.update_actors_tree())

    def create_trends_tab(self):
        trends_frame = ttk.Frame(self.notebook)
        self.notebook.add(trends_frame, text="Search Trends")

        # Add trends visualization here
        ttk.Label(trends_frame, text="Search trends visualization will be added here",
                  style='Header.TLabel').pack(pady=20)

    def create_recent_searches_frame(self, parent):
        searches_frame = ttk.LabelFrame(parent, text="Recent Searches", padding="5")
        searches_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

        # Create recent searches tree
        self.searches_tree = ttk.Treeview(
            searches_frame,
            columns=('Time', 'User ID', 'Username', 'Query', 'Platform', 'Type'),
            show='headings'
        )

        # Configure columns
        columns = {
            'Time': 150,
            'User ID': 100,
            'Username': 150,
            'Query': 200,
            'Platform': 100,
            'Type': 100
        }

        for col, width in columns.items():
            self.searches_tree.heading(col, text=col)
            self.searches_tree.column(col, width=width)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(searches_frame, orient=tk.VERTICAL,
                                  command=self.searches_tree.yview)
        self.searches_tree.configure(yscrollcommand=scrollbar.set)

        # Grid layout
        self.searches_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

    def create_search_tree(self, period):
        frame = ttk.Frame(self.time_notebook)
        self.time_notebook.add(frame, text=period)

        tree = ttk.Treeview(frame, columns=('Rank', 'Query', 'Count'), show='headings')

        # Configure columns
        tree.heading('Rank', text='#')
        tree.heading('Query', text='Search Query')
        tree.heading('Count', text='Count')

        tree.column('Rank', width=50)
        tree.column('Query', width=300)
        tree.column('Count', width=100)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        # Grid layout
        tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        return tree

    def create_actors_tree(self, parent):
        tree = ttk.Treeview(
            parent,
            columns=('Rank', 'Actor', 'Searches', 'Last Search'),
            show='headings'
        )

        # Configure columns
        tree.heading('Rank', text='#')
        tree.heading('Actor', text='Actor Name')
        tree.heading('Searches', text='Total Searches')
        tree.heading('Last Search', text='Last Searched')

        tree.column('Rank', width=50)
        tree.column('Actor', width=200)
        tree.column('Searches', width=100)
        tree.column('Last Search', width=150)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        # Grid layout
        tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        return tree

    def configure_grid_weights(self, container):
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(2, weight=2)  # Search notebook takes more space
        container.rowconfigure(3, weight=1)  # Recent searches takes less space

    def update_statistics(self):
        try:
            with sqlite3.connect(self.db.db_name) as conn:
                cursor = conn.cursor()

                # Get various statistics
                cursor.execute('SELECT COUNT(DISTINCT user_id) FROM user_searches')
                total_users = cursor.fetchone()[0]

                cursor.execute('''
                    SELECT COUNT(DISTINCT user_id) FROM user_searches 
                    WHERE date(search_time) = date('now')
                ''')
                daily_users = cursor.fetchone()[0]

                cursor.execute('SELECT COUNT(*) FROM user_searches')
                total_searches = cursor.fetchone()[0]

                cursor.execute('SELECT COUNT(*) FROM user_searches WHERE is_actor = 1')
                actor_searches = cursor.fetchone()[0]

                cursor.execute('''
                    SELECT COUNT(*) FROM user_searches 
                    WHERE date(search_time) = date('now')
                ''')
                today_searches = cursor.fetchone()[0]

                # Update statistics variables
                self.stats_vars['total_users'].set(f"Total Users: {total_users:,}")
                self.stats_vars['daily_users'].set(f"Today's Users: {daily_users:,}")
                self.stats_vars['total_searches'].set(f"Total Searches: {total_searches:,}")
                self.stats_vars['actor_searches'].set(f"Actor Searches: {actor_searches:,}")
                self.stats_vars['today_searches'].set(f"Today's Searches: {today_searches:,}")

        except Exception as e:
            logging.error(f"Error updating statistics: {e}")
            messagebox.showerror("Error", "Failed to update statistics")

    # Replace the existing update_actors_tree method with this fixed version:

    def update_actors_tree(self):
        try:
            with sqlite3.connect(self.db.db_name) as conn:
                cursor = conn.cursor()
                limit = int(self.limit_var.get())
                period = self.period_var.get()

                # Clear existing items first
                for item in self.actors_tree.get_children():
                    self.actors_tree.delete(item)

                # Build query based on selected time period
                time_clause = self.get_time_clause(period)

                # Modified query to handle NULL values and ensure proper date formatting
                query = f'''
                    SELECT 
                        query,
                        COUNT(*) as search_count,
                        MAX(datetime(search_time)) as last_search
                    FROM user_searches
                    WHERE is_actor = 1
                    {time_clause}
                    GROUP BY query
                    ORDER BY search_count DESC
                    LIMIT ?
                '''

                cursor.execute(query, (limit,))
                results = cursor.fetchall()

                # Insert new data with error handling for each row
                for rank, row in enumerate(results, 1):
                    try:
                        actor, count, last_search = row

                        # Handle potential NULL values
                        if last_search is None:
                            last_search_formatted = "N/A"
                        else:
                            try:
                                last_search_formatted = datetime.strptime(
                                    last_search, '%Y-%m-%d %H:%M:%S'
                                ).strftime('%Y-%m-%d %H:%M')
                            except ValueError:
                                last_search_formatted = "Invalid Date"

                        self.actors_tree.insert('', 'end', values=(
                            rank,
                            actor or "Unknown",
                            count or 0,
                            last_search_formatted
                        ))
                    except Exception as row_error:
                        logging.error(f"Error processing actor row: {row_error}")
                        continue  # Skip problematic rows instead of failing completely

        except sqlite3.Error as db_error:
            logging.error(f"Database error in update_actors_tree: {db_error}")
            messagebox.showerror("Database Error", "Failed to retrieve actor rankings")
        except Exception as e:
            logging.error(f"Unexpected error in update_actors_tree: {e}")
            messagebox.showerror("Error", "Failed to update actors rankings")

    # Also add this helper method if it's not already present:
    def get_time_clause(self, period):
        clauses = {
            "All Time": "",
            "Today": "AND date(search_time) = date('now', 'localtime')",
            "This Week": "AND date(search_time) >= date('now', '-7 days', 'localtime')",
            "This Month": "AND date(search_time) >= date('now', '-30 days', 'localtime')",
            "This Year": "AND date(search_time) >= date('now', '-1 year', 'localtime')"
        }
        return clauses.get(period, "")

    def update_time_based_searches(self):
        try:
            with sqlite3.connect(self.db.db_name) as conn:
                cursor = conn.cursor()

                # Update today's searches
                self.update_period_tree(cursor, self.trees['today'],
                                        "date(search_time) = date('now')")

                # Update yesterday's searches
                self.update_period_tree(cursor, self.trees['yesterday'],
                                        "date(search_time) = date('now', '-1 day')")

                # Update this week's searches
                self.update_period_tree(cursor, self.trees['week'],
                                        "date(search_time) >= date('now', '-7 days')")

                # Update this month's searches
                self.update_period_tree(cursor, self.trees['month'],
                                        "date(search_time) >= date('now', '-30 days')")

                # Update this year's searches
                self.update_period_tree(cursor, self.trees['year'],
                                        "date(search_time) >= date('now', '-1 year')")

        except Exception as e:
            logging.error(f"Error updating time-based searches: {e}")
            messagebox.showerror("Error", "Failed to update search statistics")

    def update_period_tree(self, cursor, tree, time_condition):
        query = f'''
               SELECT query, COUNT(*) as count
               FROM user_searches
               WHERE {time_condition}
               GROUP BY query
               ORDER BY count DESC
               LIMIT 10
           '''
        cursor.execute(query)

        # Clear existing items
        for item in tree.get_children():
            tree.delete(item)

        # Insert new data
        for rank, (query, count) in enumerate(cursor.fetchall(), 1):
            tree.insert('', 'end', values=(rank, query, count))

    def update_recent_searches(self):
        try:
            with sqlite3.connect(self.db.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                       SELECT 
                           datetime(search_time), 
                           user_id, 
                           username, 
                           query, 
                           platform,
                           CASE WHEN is_actor = 1 THEN 'Actor' ELSE 'General' END as search_type
                       FROM user_searches 
                       ORDER BY search_time DESC 
                       LIMIT 50
                   ''')

                # Clear existing items
                for item in self.searches_tree.get_children():
                    self.searches_tree.delete(item)

                # Insert new data
                for row in cursor.fetchall():
                    # Format datetime
                    timestamp = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
                    formatted_time = timestamp.strftime('%Y-%m-%d %H:%M')
                    values = (formatted_time,) + row[1:]
                    self.searches_tree.insert('', 'end', values=values)

        except Exception as e:
            logging.error(f"Error updating recent searches: {e}")
            messagebox.showerror("Error", "Failed to update recent searches")

    def create_trends_tab(self):
        trends_frame = ttk.Frame(self.notebook)
        self.notebook.add(trends_frame, text="Search Trends")

        # Create control panel
        control_frame = ttk.Frame(trends_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        # Time range selector
        ttk.Label(control_frame, text="Time Range:").pack(side=tk.LEFT, padx=5)
        self.trend_range = ttk.Combobox(control_frame, values=[
            "Last 24 Hours", "Last 7 Days", "Last 30 Days", "Last Year"
        ], width=15)
        self.trend_range.set("Last 7 Days")
        self.trend_range.pack(side=tk.LEFT, padx=5)

        # Trend type selector
        ttk.Label(control_frame, text="Trend Type:").pack(side=tk.LEFT, padx=5)
        self.trend_type = ttk.Combobox(control_frame, values=[
            "Search Volume", "Popular Queries", "User Activity"
        ], width=15)
        self.trend_type.set("Search Volume")
        self.trend_type.pack(side=tk.LEFT, padx=5)

        # Create refresh button
        ttk.Button(control_frame, text="Update Trends",
                   command=self.update_trends).pack(side=tk.LEFT, padx=5)

        # Create trend display area with canvas
        self.trend_canvas = tk.Canvas(trends_frame, bg='white')
        self.trend_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Bind update events
        self.trend_range.bind('<<ComboboxSelected>>', lambda e: self.update_trends())
        self.trend_type.bind('<<ComboboxSelected>>', lambda e: self.update_trends())

    def update_trends(self):
        try:
            trend_type = self.trend_type.get()
            time_range = self.trend_range.get()

            # Clear previous trend display
            self.trend_canvas.delete("all")

            # Get trend data based on selection
            data = self.get_trend_data(trend_type, time_range)

            if not data:
                self.trend_canvas.create_text(
                    self.trend_canvas.winfo_width() // 2,
                    self.trend_canvas.winfo_height() // 2,
                    text="No data available for selected period",
                    font=('Helvetica', 12)
                )
                return

            # Draw the trend visualization
            self.draw_trend_visualization(data, trend_type)

        except Exception as e:
            logging.error(f"Error updating trends: {e}")
            messagebox.showerror("Error", "Failed to update trends visualization")

    def get_trend_data(self, trend_type, time_range):
        try:
            with sqlite3.connect(self.db.db_name) as conn:
                cursor = conn.cursor()

                # Convert time range to SQL
                time_clause = self.get_time_clause_for_trends(time_range)

                if trend_type == "Search Volume":
                    query = f'''
                        SELECT 
                            date(search_time) as search_date,
                            COUNT(*) as search_count
                        FROM user_searches
                        WHERE {time_clause}
                        GROUP BY date(search_time)
                        ORDER BY search_date
                    '''
                elif trend_type == "Popular Queries":
                    query = f'''
                        SELECT 
                            query,
                            COUNT(*) as query_count
                        FROM user_searches
                        WHERE {time_clause}
                        GROUP BY query
                        ORDER BY query_count DESC
                        LIMIT 10
                    '''
                else:  # User Activity
                    query = f'''
                        SELECT 
                            date(search_time) as activity_date,
                            COUNT(DISTINCT user_id) as active_users
                        FROM user_searches
                        WHERE {time_clause}
                        GROUP BY date(search_time)
                        ORDER BY activity_date
                    '''

                cursor.execute(query)
                return cursor.fetchall()

        except Exception as e:
            logging.error(f"Error fetching trend data: {e}")
            return None

    def get_time_clause_for_trends(self, time_range):
        clauses = {
            "Last 24 Hours": "search_time >= datetime('now', '-1 day', 'localtime')",
            "Last 7 Days": "search_time >= datetime('now', '-7 days', 'localtime')",
            "Last 30 Days": "search_time >= datetime('now', '-30 days', 'localtime')",
            "Last Year": "search_time >= datetime('now', '-1 year', 'localtime')"
        }
        return clauses.get(time_range, "1=1")

    def draw_trend_visualization(self, data, trend_type):
        try:
            # Get canvas dimensions
            width = self.trend_canvas.winfo_width()
            height = self.trend_canvas.winfo_height()

            # Check for valid dimensions
            if width <= 1 or height <= 1:
                self.trend_canvas.update()
                width = self.trend_canvas.winfo_width()
                height = self.trend_canvas.winfo_height()

                # If still invalid, set minimum dimensions
                if width <= 1 or height <= 1:
                    width = 600
                    height = 400

            padding = 40

            # Clear previous drawings
            self.trend_canvas.delete("all")

            # Draw axes
            self.trend_canvas.create_line(padding, height - padding,
                                          width - padding, height - padding,
                                          width=2)  # X axis
            self.trend_canvas.create_line(padding, height - padding,
                                          padding, padding,
                                          width=2)  # Y axis

            if not data:
                # Draw "No data" message
                self.trend_canvas.create_text(
                    width // 2,
                    height // 2,
                    text="No data available for selected period",
                    font=('Helvetica', 12)
                )
                return

            if trend_type == "Popular Queries":
                self.draw_bar_chart(data, width, height, padding)
            else:
                self.draw_line_chart(data, width, height, padding)

            # Add title
            self.trend_canvas.create_text(
                width // 2,
                padding // 2,
                text=f"{trend_type} Over Time",
                font=('Helvetica', 14, 'bold')
            )

        except Exception as e:
            logging.error(f"Error in draw_trend_visualization: {str(e)}")
            # Show error on canvas
            self.trend_canvas.delete("all")
            self.trend_canvas.create_text(
                self.trend_canvas.winfo_width() // 2,
                self.trend_canvas.winfo_height() // 2,
                text=f"Error drawing visualization: {str(e)}",
                font=('Helvetica', 10),
                fill='red'
            )

    def draw_line_chart(self, data, width, height, padding):
        try:
            # Calculate scales
            x_scale = (width - 2 * padding) / max(len(data) - 1, 1)

            # Always start y-axis from 0 to show full range
            min_y = 0  # Changed from min(row[1] for row in data)
            max_y = max(row[1] for row in data)
            y_range = max(max_y - min_y, 1)  # Prevent division by zero

            # Add 10% padding to the top of the chart for better visualization
            y_range = y_range * 1.1

            # Recalculate y_scale with the full range
            y_scale = (height - 2 * padding) / y_range

            # Plot points and lines
            points = []
            for i, (date, value) in enumerate(data):
                x = padding + (i * x_scale)
                # Calculate y position from the bottom (height - padding)
                y = height - (padding + (value - min_y) * y_scale)
                points.append((x, y))

                # Draw point
                self.trend_canvas.create_oval(x - 3, y - 8, x + 3, y + 3,
                                              fill='blue', outline='darkblue')

                # Draw date label
                date_str = str(date).split()[0] if isinstance(date, datetime) else str(date)
                self.trend_canvas.create_text(
                    x, height - padding + 20,
                    text=date_str,
                    angle=45,
                    anchor='ne'
                )

                # Draw value label above point
                self.trend_canvas.create_text(
                    x, y - 15,
                    text=str(int(value)),
                    anchor='s',
                    font=('Helvetica', 8)
                )

            # Connect points with lines
            if len(points) > 1:
                self.trend_canvas.create_line(points, fill='blue', smooth=1, width=2)

            # Add Y-axis labels with more frequent intervals
            num_labels = 6  # Increased number of labels
            for i in range(num_labels):
                value = min_y + (y_range * i / (num_labels - 1))
                y_pos = height - (padding + (value - min_y) * y_scale)
                self.trend_canvas.create_text(
                    padding - 10,
                    y_pos,
                    text=f"{int(value):,}",
                    anchor='e'
                )

            # Add grid lines for better readability
            for i in range(num_labels):
                y_pos = height - (padding + (y_range * i / (num_labels - 1)) * y_scale)
                self.trend_canvas.create_line(
                    padding, y_pos,
                    width - padding, y_pos,
                    fill='lightgray', dash=(2, 4)
                )

        except Exception as e:
            logging.error(f"Error in draw_line_chart: {str(e)}")
            raise

    def draw_bar_chart(self, data, width, height, padding):
        try:
            # Calculate bar dimensions
            max_bars = min(len(data), 10)  # Limit to 10 bars
            bar_width = (width - 2 * padding) / max_bars
            max_y = max(row[1] for row in data[:max_bars])
            y_scale = (height - 2 * padding) / max_y

            # Draw bars
            for i, (query, value) in enumerate(data[:max_bars]):
                x1 = padding + (i * bar_width) + 5
                y1 = height - padding
                x2 = x1 + bar_width - 10
                y2 = height - (padding + value * y_scale)

                # Draw bar
                self.trend_canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill='lightblue',
                    outline='blue'
                )

                # Draw value on top of bar
                self.trend_canvas.create_text(
                    (x1 + x2) / 2,
                    y2 - 10,
                    text=str(value),
                    anchor='s'
                )

                # Draw query label
                truncated_query = query[:15] + '...' if len(str(query)) > 15 else str(query)
                self.trend_canvas.create_text(
                    (x1 + x2) / 2,
                    height - padding + 20,
                    text=truncated_query,
                    angle=45,
                    anchor='ne'
                )

            # Add Y-axis labels
            num_labels = 5
            for i in range(num_labels):
                value = max_y * i / (num_labels - 1)
                y_pos = height - (padding + value * y_scale)
                self.trend_canvas.create_text(
                    padding - 10,
                    y_pos,
                    text=f"{int(value):,}",
                    anchor='e'
                )

        except Exception as e:
            logging.error(f"Error in draw_bar_chart: {str(e)}")
            raise

    def refresh_data(self):
        """Manually refresh all data in the dashboard"""
        try:
            self.update_statistics()
            self.update_time_based_searches()
            self.update_recent_searches()
            self.update_actors_tree()
            messagebox.showinfo("Success", "Data refreshed successfully")
        except Exception as e:
            logging.error(f"Error refreshing data: {e}")
            messagebox.showerror("Error", "Failed to refresh data")

    def update_loop(self):
        """Background thread for automatic updates"""
        while self.should_update:
            try:
                self.update_statistics()
                self.update_time_based_searches()
                self.update_recent_searches()
                self.update_actors_tree()
                time.sleep(5)  # Update every 5 seconds
            except Exception as e:
                logging.error(f"Error in update loop: {e}")
                time.sleep(5)  # Wait before retrying

    def on_closing(self):
        """Clean up resources when closing the application"""
        try:
            self.should_update = False
            self.update_thread.join(timeout=1.0)
            self.root.destroy()
        except Exception as e:
            logging.error(f"Error during shutdown: {e}")
            self.root.destroy()


def main():
    try:
        # Create log directory if it doesn't exist
        if not os.path.exists('logs'):
            os.makedirs('logs')

        # Set up logging
        logging.basicConfig(
            filename='logs/search_analytics.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        # Start the application
        root = tk.Tk()
        app = SearchAnalyticsApp(root)
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        root.mainloop()

    except Exception as e:
        logging.critical(f"Application failed to start: {e}")
        messagebox.showerror("Error", f"Application failed to start: {str(e)}")


if __name__ == "__main__":
    main()
