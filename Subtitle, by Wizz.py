import pygame
import pysrt
import time
import requests
import os
import tempfile
import json
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import ctypes
import win32gui
import win32con
import win32api

# Initialize pygame
pygame.init()

# Constants
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 180  # Increased height for control bar and title bar
FONT_SIZE = 30
FONT_COLOR = (255, 255, 255)
BACKGROUND_ALPHA = 180  # More transparent black background
MOVE_STEP = 10
BAR_HEIGHT = 20  # Height of progress bar
TITLE_BAR_HEIGHT = 30  # Height of title bar
SEEK_STEP = 2  # Adjust forward/backward step for easier control
WINDOW_DRAGABLE = False
WINDOW_POS = [100, 100]  # Initial window position
CONTROLS_VISIBLE = True  # Track if controls are visible

# Load font
font = pygame.font.SysFont("Arial", FONT_SIZE)
small_font = pygame.font.SysFont("Arial", 20)

# OpenSubtitles API Key
API_KEY = "V4TO7c5ucYWc2T6cj95DmXC3fPBFER9J"

drag_offset = [0, 0]

def make_window_transparent():
    hwnd = pygame.display.get_wm_info()['window']
    
    # Set window style
    ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, 
                          ex_style | win32con.WS_EX_LAYERED | win32con.WS_EX_TOPMOST)
    
    # Set the window to be transparent
    win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(0,0,0), 0, win32con.LWA_COLORKEY)
    
    # Make the window stay on top
    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                         win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
    
def move_window(x, y):
    hwnd = pygame.display.get_wm_info()['window']
    win32gui.SetWindowPos(hwnd, 0, x, y, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)

# Function to search for subtitles online
def search_subtitles():
    global subtitles, total_duration, start_time, paused
    
    def create_search_window():
        nonlocal srt_file_result
        search_window = tk.Toplevel(root)
        search_window.title("Search Subtitles")
        search_window.geometry("600x400")
        
        # Search frame
        search_frame = tk.Frame(search_window)
        search_frame.pack(fill='x', padx=10, pady=5)
        
        search_entry = tk.Entry(search_frame, width=40)
        search_entry.pack(side='left', padx=5)
        search_entry.insert(0, "Enter movie or TV show name")
        search_entry.bind('<FocusIn>', lambda e: search_entry.delete(0, 'end') if search_entry.get() == "Enter movie or TV show name" else None)
        
        results_listbox = tk.Listbox(search_window, width=70, height=15)
        results_listbox.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Add scrollbar to listbox
        scrollbar = tk.Scrollbar(search_window)
        scrollbar.pack(side='right', fill='y')
        results_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=results_listbox.yview)
        
        subtitle_results = []  # Store the full subtitle data
        
        def perform_search():
            movie_name = search_entry.get()
            if not movie_name or movie_name == "Enter movie or TV show name":
                return
                
            url = "https://api.opensubtitles.com/api/v1/subtitles"
            headers = {"Api-Key": API_KEY, "Content-Type": "application/json"}
            params = {"query": movie_name, "languages": "en"}
            
            try:
                response = requests.get(url, headers=headers, params=params)
                if response.status_code == 200:
                    results = response.json().get("data", [])
                    results_listbox.delete(0, tk.END)  # Clear current results
                    subtitle_results.clear()
                    
                    if results:
                        for sub in results:
                            # Format the display string with more details
                            release_name = sub['attributes']['release'] or 'Unknown'
                            language = sub['attributes']['language']
                            download_count = sub['attributes'].get('download_count', 0)
                            display_text = f"{release_name} ({language}) - Downloads: {download_count}"
                            
                            results_listbox.insert(tk.END, display_text)
                            subtitle_results.append(sub)  # Store the full subtitle data
                    else:
                        results_listbox.insert(tk.END, "No results found")
            except Exception as e:
                messagebox.showerror("Error", f"Search failed: {str(e)}")
        
        def select_subtitle():
            nonlocal srt_file_result, subtitle_results  # Make sure we can access subtitle_results
            selection = results_listbox.curselection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a subtitle")
                return
            
            try:
                print(f"Selected index: {selection[0]}")  # Debug print
                print(f"Number of results: {len(subtitle_results)}")  # Debug print
                
                subtitle_data = subtitle_results[selection[0]]
                print(f"Selected subtitle data: {subtitle_data['attributes']['release']}")  # Debug print
                
                file_id = subtitle_data["attributes"]["files"][0]["file_id"]
                print(f"File ID: {file_id}")  # Debug print
                
                # Download URL construction
                download_url = "https://api.opensubtitles.com/api/v1/download"
                download_data = {"file_id": file_id}
                headers = {
                    "Api-Key": API_KEY,
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
                
                # Make download request
                print("Sending download request...")  # Debug print
                download_response = requests.post(download_url, headers=headers, json=download_data)
                print(f"Download response status: {download_response.status_code}")  # Debug print
                
                if download_response.status_code == 200:
                    download_link = download_response.json().get("link")
                    if download_link:
                        print(f"Got download link: {download_link}")  # Debug print
                        # Download the actual subtitle file
                        subtitle_response = requests.get(download_link)
                        if subtitle_response.status_code == 200:
                            # Use temp directory instead of current directory
                            temp_dir = tempfile.gettempdir()
                            srt_file = os.path.join(temp_dir, "downloaded_subtitle.srt")
                            with open(srt_file, "wb") as file:
                                file.write(subtitle_response.content)
                            
                            srt_file_result = srt_file  # Store the result
                            print(f"Saved subtitle to: {srt_file}")  # Debug print
                            messagebox.showinfo("Success", "Subtitles loaded successfully!")
                            search_window.destroy()
                    else:
                        print("No download link in response")  # Debug print
                        messagebox.showerror("Error", "No download link available")
                else:
                    print(f"Download request failed: {download_response.text}")  # Debug print
                    messagebox.showerror("Error", f"Download request failed: {download_response.status_code}")
            except Exception as e:
                print(f"Error in select_subtitle: {str(e)}")  # Debug print
                messagebox.showerror("Error", f"Failed to download subtitle: {str(e)}")
        
        def upload_subtitle():
            srt_file = filedialog.askopenfilename(title="Select SRT File", filetypes=[("SubRip Subtitle", "*.srt")])
            if srt_file:
                nonlocal srt_file_result
                srt_file_result = srt_file
                search_window.destroy()
        
        # Create buttons
        search_button = tk.Button(search_frame, text="Search", command=perform_search)
        search_button.pack(side='left', padx=5)
        
        upload_button = tk.Button(search_frame, text="Upload Subtitles", command=upload_subtitle)
        upload_button.pack(side='right', padx=5)
        
        # Buttons frame
        button_frame = tk.Frame(search_window)
        button_frame.pack(fill='x', padx=10, pady=5)
        
        select_button = tk.Button(button_frame, text="Use Selected Subtitle", command=select_subtitle)
        select_button.pack(side='right', padx=5)
        
        cancel_button = tk.Button(button_frame, text="Cancel", command=search_window.destroy)
        cancel_button.pack(side='right', padx=5)
        
        # Bind Enter key to search and double-click to select
        search_entry.bind('<Return>', lambda e: perform_search())
        results_listbox.bind('<Double-Button-1>', lambda e: select_subtitle())
        
        # Center the window
        search_window.update_idletasks()
        width = search_window.winfo_width()
        height = search_window.winfo_height()
        x = (search_window.winfo_screenwidth() // 2) - (width // 2)
        y = (search_window.winfo_screenheight() // 2) - (height // 2)
        search_window.geometry(f'{width}x{height}+{x}+{y}')
        
        search_window.focus_force()
        search_entry.focus_set()
        
        # Make the window modal
        search_window.grab_set()
        search_window.wait_window()
        return srt_file_result
        
        # Buttons frame
        button_frame = tk.Frame(search_window)
        button_frame.pack(fill='x', padx=10, pady=5)
        
        search_button = tk.Button(search_frame, text="Search", command=perform_search)
        search_button.pack(side='left', padx=5)
        
        select_button = tk.Button(button_frame, text="Use Selected Subtitle", command=select_subtitle)
        select_button.pack(side='right', padx=5)
        
        cancel_button = tk.Button(button_frame, text="Cancel", command=search_window.destroy)
        cancel_button.pack(side='right', padx=5)
        
        # Bind Enter key to search
        search_entry.bind('<Return>', lambda e: perform_search())
        # Bind double-click to select
        results_listbox.bind('<Double-Button-1>', lambda e: select_subtitle())
        
        # Center the window
        search_window.update_idletasks()
        width = search_window.winfo_width()
        height = search_window.winfo_height()
        x = (search_window.winfo_screenwidth() // 2) - (width // 2)
        y = (search_window.winfo_screenheight() // 2) - (height // 2)
        search_window.geometry(f'{width}x{height}+{x}+{y}')
        
        search_window.focus_force()
        search_entry.focus_set()
        
        # Make the window modal
        search_window.grab_set()
        search_window.wait_window()
        
        return srt_file_result
    
    srt_file_result = None
    result = create_search_window()
    if result:
        subtitles = load_srt(result)
        total_duration = subtitles[-1][1] if subtitles else 0
        start_time = time.time()
        paused = False
    return result

# Function to download subtitles
def download_subtitle(url):
    headers = {"Api-Key": API_KEY, "Content-Type": "application/json"}
    response = requests.post(url, headers=headers)  # Note: Changed to POST request
    if response.status_code == 200:
        download_link = response.json().get("link")
        if download_link:
            # Download the actual subtitle file
            subtitle_response = requests.get(download_link)
            if subtitle_response.status_code == 200:
                srt_file = "downloaded_subtitle.srt"
                with open(srt_file, "wb") as file:
                    file.write(subtitle_response.content)
                return srt_file
    return None

# Load subtitles
def load_srt(file_path):
    subs = pysrt.open(file_path)
    return [(sub.start.ordinal / 1000, sub.end.ordinal / 1000, sub.text.replace('\n', ' ')) for sub in subs]

# Open file dialog or fetch online subtitles
# Open file dialog or fetch online subtitles
# Open file dialog or fetch online subtitles
# Open file dialog or fetch online subtitles
root = tk.Tk()
root.withdraw()

def initial_subtitle_load():
    # First try file selection
    srt_file = filedialog.askopenfilename(title="Select SRT File", filetypes=[("SubRip Subtitle", "*.srt")])
    
    # If file selection was cancelled, show search window immediately
    if not srt_file:
        srt_file = search_subtitles()
    return srt_file

# Get initial subtitles
srt_file = initial_subtitle_load()
subtitles = load_srt(srt_file) if srt_file else []
total_duration = subtitles[-1][1] if subtitles else 0

# Pygame setup
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.NOFRAME | pygame.SRCALPHA)
pygame.display.set_caption("Movable Subtitle Player")
clock = pygame.time.Clock()

make_window_transparent()

# Create transparent surface
transparent_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

# Subtitle position
sub_x, sub_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT - 60

start_time = time.time()
paused = False

def draw_top_bar():
    if not CONTROLS_VISIBLE:
        return None, None, None, None
        
    # Title bar area - full width of window
    title_bar_rect = pygame.Rect(0, 0, SCREEN_WIDTH, TITLE_BAR_HEIGHT)
    pygame.draw.rect(transparent_surface, (20, 20, 20, BACKGROUND_ALPHA), title_bar_rect)
    title_text = small_font.render("Subtitle Player", True, (255, 255, 255))
    transparent_surface.blit(title_text, (10, 5))
    
    # Add "Made by WK" text centered
    made_by_text = small_font.render("Made by WK", True, (255, 255, 255))
    made_by_rect = made_by_text.get_rect(center=(SCREEN_WIDTH // 2, TITLE_BAR_HEIGHT // 2))
    transparent_surface.blit(made_by_text, made_by_rect)
    
    # Add search button
    search_button = pygame.Rect(SCREEN_WIDTH - 190, 5, 100, 20)
    pygame.draw.rect(transparent_surface, (0, 100, 200, BACKGROUND_ALPHA), search_button)
    search_text = small_font.render("Search Subs", True, (255, 255, 255))
    transparent_surface.blit(search_text, (SCREEN_WIDTH - 180, 5))
    
    close_button = pygame.Rect(SCREEN_WIDTH - 40, 5, 30, 20)
    pygame.draw.rect(transparent_surface, (200, 0, 0, BACKGROUND_ALPHA), close_button)
    close_text = small_font.render("X", True, (255, 255, 255))
    transparent_surface.blit(close_text, (SCREEN_WIDTH - 30, 5))
    
    minimize_button = pygame.Rect(SCREEN_WIDTH - 80, 5, 30, 20)
    pygame.draw.rect(transparent_surface, (100, 100, 100, BACKGROUND_ALPHA), minimize_button)
    min_text = small_font.render("_", True, (255, 255, 255))
    transparent_surface.blit(min_text, (SCREEN_WIDTH - 70, 5))
    
    return close_button, minimize_button, search_button, title_bar_rect

running = True
while running:
    transparent_surface.fill((0, 0, 0, BACKGROUND_ALPHA))
    
    if not paused:
        elapsed_time = time.time() - start_time
    
    # Draw top bar
    close_btn, min_btn, search_btn, title_bar_rect = draw_top_bar()
    
    # Find current subtitle and scale text to fit
    for start, end, text in subtitles:
        if start <= elapsed_time <= end:
            text_surface = font.render(text, True, FONT_COLOR)
            while text_surface.get_width() > SCREEN_WIDTH - 40:  # Shrink text if too wide
                FONT_SIZE -= 1
                font = pygame.font.SysFont("Arial", FONT_SIZE)
                text_surface = font.render(text, True, FONT_COLOR)
            text_rect = text_surface.get_rect(center=(sub_x, sub_y))
            transparent_surface.blit(text_surface, text_rect)
            break
    
    # Draw progress bar only if controls are visible
    if CONTROLS_VISIBLE:
        progress = elapsed_time / total_duration if total_duration else 0
        bar_width = int(progress * SCREEN_WIDTH)
        pygame.draw.rect(transparent_surface, (50, 50, 50, BACKGROUND_ALPHA), (0, SCREEN_HEIGHT - BAR_HEIGHT, SCREEN_WIDTH, BAR_HEIGHT))
        pygame.draw.rect(transparent_surface, (0, 255, 0, BACKGROUND_ALPHA), (0, SCREEN_HEIGHT - BAR_HEIGHT, bar_width, BAR_HEIGHT))
    
    # Blit transparent surface onto screen
    screen.blit(transparent_surface, (0, 0))
    
    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_q:  # Toggle controls visibility
                CONTROLS_VISIBLE = not CONTROLS_VISIBLE
            elif event.key == pygame.K_RIGHTBRACKET:
                start_time -= SEEK_STEP
            elif event.key == pygame.K_LEFTBRACKET:
                start_time += SEEK_STEP
            elif event.key == pygame.K_SPACE:
                paused = not paused
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            if event.button == 1:  # Left click
                if CONTROLS_VISIBLE:
                    if close_btn.collidepoint(mouse_x, mouse_y):
                        running = False
                    elif min_btn.collidepoint(mouse_x, mouse_y):
                        pygame.display.iconify()
                    elif search_btn.collidepoint(mouse_x, mouse_y):
                        if search_subtitles():
                            start_time = time.time()
                            elapsed_time = 0
                            paused = False
                    elif mouse_y <= TITLE_BAR_HEIGHT:  # Click in title bar area
                        WINDOW_DRAGABLE = True
                        drag_offset = [mouse_x, mouse_y]
                    elif mouse_y >= SCREEN_HEIGHT - BAR_HEIGHT:  # Click on progress bar
                        start_time = time.time() - (mouse_x / SCREEN_WIDTH * total_duration)
                else:  # When controls are hidden, allow dragging from anywhere
                    WINDOW_DRAGABLE = True
                    drag_offset = [mouse_x, mouse_y]
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                WINDOW_DRAGABLE = False
        elif event.type == pygame.MOUSEMOTION:
            if WINDOW_DRAGABLE:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                new_x = WINDOW_POS[0] + mouse_x - drag_offset[0]
                new_y = WINDOW_POS[1] + mouse_y - drag_offset[1]
                WINDOW_POS = [new_x, new_y]
                move_window(new_x, new_y)

    # Add semi-transparent background behind text in the subtitle rendering section
    for start, end, text in subtitles:
        if start <= elapsed_time <= end:
            text_surface = font.render(text, True, FONT_COLOR)
            while text_surface.get_width() > SCREEN_WIDTH - 40:
                FONT_SIZE -= 1
                font = pygame.font.SysFont("Arial", FONT_SIZE)
                text_surface = font.render(text, True, FONT_COLOR)
            text_rect = text_surface.get_rect(center=(sub_x, sub_y))
            
            # Draw semi-transparent background behind text
            padding = 10
            bg_rect = pygame.Rect(text_rect.x - padding, text_rect.y - padding,
                                text_rect.width + 2*padding, text_rect.height + 2*padding)
            pygame.draw.rect(transparent_surface, (0, 0, 0, BACKGROUND_ALPHA), bg_rect)
            transparent_surface.blit(text_surface, text_rect)
            break
    
    pygame.display.flip()
    clock.tick(30)

pygame.quit()
