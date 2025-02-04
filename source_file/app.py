import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import pytesseract
from PIL import Image, ImageTk
from datetime import datetime, timedelta
from tkinter import PhotoImage
import re
import subprocess
import platform
import pandas as pd
import customtkinter
import vlc
import ctypes
import os
import threading
import platform
from bs4 import BeautifulSoup
import requests
import csv
import pandas as pd
import tempfile
import os
import sys

def get_ffmpeg_path():
    if getattr(sys, 'frozen', False):
        ffmpeg_path = os.path.join(sys._MEIPASS, "ffmpeg-v1", "bin", "ffmpeg.exe")
    else:
        ffmpeg_path = os.path.join(os.path.dirname(__file__), "ffmpeg-v1", "bin", "ffmpeg.exe")
    
    return ffmpeg_path


if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = os.path.join(os.path.dirname(__file__), "Tesseract-OCR", "tesseract.exe")
else:
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'


def extract_timestamp(frame, x=0, y=0, w=1000, h=90):
    try:
        # Crop the frame to the area where the timestamp is expected
        timestamp_crop = frame[y:y+h, x:x+w]
        # cv2.imwrite("timestamp_crop.jpg", timestamp_crop)  # Save the cropped image for debugging

        # Convert to grayscale and apply thresholding
        timestamp_grey = cv2.cvtColor(timestamp_crop, cv2.COLOR_BGR2GRAY)
        _, timestamp_thresh = cv2.threshold(timestamp_grey, 127, 255, cv2.THRESH_BINARY)

        # Use Tesseract to extract text from the thresholded image
        candidate_str = pytesseract.image_to_string(timestamp_thresh, config='--psm 6')
        print(f"Extracted text from image: {candidate_str}")

        # Define the regex pattern for matching the timestamp
        regex_str = r'(?i)(?:Ba\s*)?Date:\s*(\d{4}-\d{2}-\d{2})\s*Time:\s*(\d{1,2}:\d{2}:\d{2}\s*(?:AM|PM))\s*Frame:\s*(\d{2}:\d{2}:\d{2}:\d{2})'
        match = re.search(regex_str, candidate_str)
        if match:
            date_str, time_str, frame_str = match.groups()
            print(f"Extracted timestamp - Date: {date_str}, Time: {time_str}, Frame: {frame_str}")
            return date_str, time_str, frame_str
        else:
            print("No match found for the timestamp.")
    except Exception as e:
        print(f"Error extracting timestamp: {e}")

    return None, None, None


def get_video_timestamp(video_path, frame_position):
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_position)
    ret, frame = cap.read()
    # cv2.imwrite("frame.jpg",frame)
    cap.release()
    if ret:
        return extract_timestamp(frame)
    # cv2.imwrite("frame1.jpg",frame)
    return None, None, None


def get_initial_time(video_path):
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Error: The file {video_path} does not exist.")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Error: Cannot open video file {video_path}.")

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Total frames in video: {frame_count}")

    # Process only the first few frames to ensure accurate timestamp extraction
    end_frame = min(100, frame_count)  
    for i in range(0, end_frame):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, frame = cap.read()
        if ret:
            print(f"Processing frame {i}")
            # Debugging: Save the frame to check if it's being read correctly
            # cv2.imwrite(f"debug_frame_{i}.jpg", frame)

            # Extract the timestamp from the current frame
            date_str, time_str, _ = get_video_timestamp(video_path, i)
            if time_str:
                print(f"Extracted initial time: {time_str}")
                cap.release()  # Release the capture here after processing
                return time_str
            else:
                print(f"Failed to extract initial time from frame {i}")

    cap.release()
    print("Error: Could not extract initial time from the first few frames.")
    return "00:00:00 AM"


def get_video_end_time(video_path):
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Error: The file {video_path} does not exist.")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Error: Cannot open video file {video_path}.")

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Total frames in video: {frame_count}")

    # Adjust the range to ensure it does not exceed the total number of frames
    start_frame = max(0, frame_count - 100)  
    for i in range(frame_count - 1, start_frame - 1, -1):  
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, frame = cap.read()
        if ret:
            print(f"The saved frame[image] count --- >{i}")
            # cv2.imwrite("debug_last_frame.jpg", frame)
            date_str, time_str, _ = get_video_timestamp(video_path, i)
            if time_str:
                print(f"Extracted end time: {time_str}")
                cap.release()  # Release the capture here after processing
                return time_str
            else:
                print(f"Failed to extract end time from frame {i}")

    cap.release()  
    print("Error: Could not read any of the last frames of the video.")
    return '00:00:00'



def parse_time(time_str):
    """Parses a time string into a datetime object, handling multiple formats."""
    time_str = time_str.strip()  # Remove any leading or trailing whitespace
    
    formats = ['%I:%M:%S %p', '%H:%M:%S']  
    for fmt in formats:
        try:
            parsed_time = datetime.strptime(time_str, fmt)
            print(f"Successfully parsed '{time_str}' using format '{fmt}' to {parsed_time}")
            return parsed_time
        except ValueError as e:
            print(f"Failed to parse '{time_str}' with format '{fmt}': {e}")
            continue
    
    print(f"Error parsing time '{time_str}' with all formats")
    return None

def time_to_seconds(time_str):
    print(f'{time_str}')
    try:
        # Check if the time string contains AM or PM
        if 'AM' in time_str or 'PM' in time_str:
            # Handle time that contains 'AM' or 'PM'
            time_str = time_str.split()[0]  
        # Try parsing the time in 24-hour format first (%H:%M:%S)
        try:
            time_obj = datetime.strptime(time_str, '%H:%M:%S')
        except ValueError:
            # If it fails, try parsing in 12-hour format
            time_obj = datetime.strptime(time_str, '%I:%M:%S %p')

        # Convert 24-hour time to 12-hour format for proper AM/PM
        time_str_12hr = time_obj.strftime('%I:%M:%S %p')
        
        print(f"Converted to 12-hour format: {time_str_12hr}")

        # Now, compute the total seconds based on the original time format
        total_seconds = time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second
        
        return total_seconds

    except ValueError:
        messagebox.showerror("Time Error", "Time format not recognized.")
        raise ValueError(f"Time format not recognized: {time_str}")


def seconds_to_time(seconds):
    return str(timedelta(seconds=seconds))

def encode_video(input_path, output_path):
    try:
        ffmpeg_path = get_ffmpeg_path()
        print(f"path to ffmpeg ------> {ffmpeg_path}")
        command = [
            ffmpeg_path,
            '-y',
            '-i', input_path,
            '-c:v', 'libx265',
            '-crf', '23', 
            '-preset', 'fast',
            '-c:a', 'aac',
            '-b:a', '192k',
            output_path
        ]
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", "Failed to encode video with ffmpeg.")



def trim_video(file_path, start_time, end_time, initial_time_str):
    start_time_sec = time_to_seconds(start_time)
    end_time_sec = time_to_seconds(end_time)
    initial_time_sec = time_to_seconds(initial_time_str)
    
    start_time_sec -= initial_time_sec
    end_time_sec -= initial_time_sec
    
    if start_time_sec >= end_time_sec:
        end_time_sec += 24 * 3600

    if start_time_sec >= end_time_sec:
        messagebox.showerror("Time Error", "Start time must be before end time.")
        return None

    # Output directory in a safe location
    output_dir = os.path.join(os.getenv('USERPROFILE'), "Documents", "trimmed_videos")
    os.makedirs(output_dir, exist_ok=True)  

    trimmed_file = os.path.join(output_dir, os.path.basename(file_path).replace('.mp4', '_trimmed.mp4'))
    print(f"Trimmed video path: {trimmed_file}")

    # Get the FFmpeg path
    ffmpeg_path = get_ffmpeg_path()

    trim_command = [
        ffmpeg_path,
        '-y',
        '-i', file_path,
        '-ss', str(start_time_sec),
        '-to', str(end_time_sec),
        '-c:v', 'libx264',
        '-crf', '18',
        '-preset', 'ultrafast',
        '-c:a', 'aac',
        '-strict', 'experimental',
        trimmed_file
    ]

    print(f"Running command: {' '.join(trim_command)}")

    try:
        result = subprocess.run(trim_command, check=True, capture_output=True, text=True)
        print("FFmpeg output:", result.stdout)
        print("FFmpeg error (if any):", result.stderr)
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg failed with error: {e.stderr}")
        messagebox.showerror("Error", "Failed to trim video.")
        return None
    except PermissionError as e:
        print(f"PermissionError: {str(e)}")
        messagebox.showerror("Permission Denied", "You do not have the required permissions to execute this operation.")
        return None
    return trimmed_file


def parse_data(raw_data):
        # Combine the raw data into a single string
        combined_data = " ".join(raw_data).replace('\xa0', '').replace('\n', ' ')
        
        # Define regex patterns for each field
        patterns = {
            "Registration Number": r"REGISTRATION NUMBER\s*:\s*(\d+)",
            "Full Name": r"FULL NAME\s*:\s*(.+?)\s*MOBILE",
            "Mobile": r"MOBILE\s*:\s*(\d+)",
            "Company": r"COMPANY\s*:\s*(.+?)\s*DESIGNATION",
            "Designation": r"DESIGNATION\s*:\s*(.+?)\s*ADDRESS:ChennaiCITY",
            "Address": r"ADDRESS\s*:\s*(.+?)\s*CITY",
            "City": r"CITY\s*:\s*(.+?)\s*STATE",
            "State": r"STATE\s*:\s*(.+?)\s*PINCODE",
            "Pincode": r"PINCODE\s*:\s*(\d+)",
            "Email": r"EMAIL\s*:\s*(\S+)"
        }
        
        # Extract data
        extracted_data = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, combined_data, re.IGNORECASE)
            extracted_data[key] = match.group(1).strip() if match else "Not Found"
        
        # Ensure values are unique
        for key in extracted_data:
            extracted_data[key] = " ".join(dict.fromkeys(extracted_data[key].split()))
        
        return extracted_data

class VideoPlayerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("XOW-POC")
        
        self.capture = None
        self.video_path = None
        self.initial_time_str = "00:00:00"
        self.end_time_str = "00:00:00"
        self.video_ended_displayed=False 
        self.tree = None
        self.setup_gui()

    def setup_gui(self):  
        # Set the VLC library path and plugin path
        vlc_dir = os.path.join(os.path.dirname(__file__), "VLC")
        print(f"VLC directory: {vlc_dir}")
        libvlc_path = os.path.join(vlc_dir, 'libvlc.dll')
        plugins_path = os.path.join(vlc_dir, 'plugins')

        # Set VLC environment variables
        os.environ['VLC_PLUGIN_PATH'] = plugins_path
        os.environ['PYTHON_VLC_LIB_PATH'] = libvlc_path

        # Verify if VLC library exists and load it using ctypes
        if os.path.exists(libvlc_path):
            print(f"VLC DLL found at: {libvlc_path}")
            try:
                # Load the DLL using the full path
                ctypes.CDLL(libvlc_path)
                print(f"VLC DLL loaded successfully from: {libvlc_path}")
            except OSError as e:
                print(f"Failed to load VLC DLL: {e}")
                raise
        else:
            print("VLC DLL not found!")
            raise FileNotFoundError(f"Could not find VLC DLL at {libvlc_path}")

        # Initialize VLC instance and player
        try:
            self.vlc_instance = vlc.Instance()  
            if self.vlc_instance is None:
                print("Failed to initialize VLC instance.")
                raise Exception("VLC instance initialization failed.")
            else:
                print("VLC instance initialized successfully.")
                self.player = self.vlc_instance.media_player_new()  
                print("VLC media player created successfully.")
        except Exception as e:
            print(f"Error initializing VLC instance or player: {e}")
            raise

        # Set up grid layout
        self.instance = vlc.Instance('--no-xlib')
        self.player = self.instance.media_player_new()

        # Left container
        self.left_container = tk.Frame(root,bg="grey",highlightbackground="black",highlightthickness=1)  # Fixed width
        self.left_container.pack(side=tk.LEFT,fill=tk.Y)  

        # left_label container
        self.lable_frame=tk.Frame(self.left_container,bg="grey")
        self.lable_frame.pack(side=tk.TOP,pady=(0, 10))
        
        # left Button video & upload
        self.button_container=tk.Frame(self.left_container,bg="grey")
        self.button_container.pack(side=tk.TOP,pady=(0, 10))

        # left Search button 
        self.search_container=tk.Frame(self.left_container,bg="grey")
        self.search_container.pack(side=tk.TOP,pady=(0, 10))

        # left trim container
        self.trim_container=tk.Frame(self.left_container,bg="grey")
        self.trim_container.pack(side=tk.TOP,pady=(0, 10))

        # Right container 
        self.right_container=tk.Frame(root,bg="white",highlightbackground="black",highlightthickness=1)
        self.right_container.pack(side=tk.RIGHT,fill=tk.BOTH,expand=True)  

        # right_video container
        self.canvas = tk.Canvas(self.right_container, width=600, height=550,bg="white")
        self.canvas.pack(side=tk.TOP,fill=tk.X)  # Expand to fill available space

        # right slider container 
        self.slider_container=tk.Frame(self.right_container,bg="white")
        self.slider_container.pack(side=tk.TOP,fill=tk.BOTH)
        
        # right button container
        self.r_button_container=tk.Frame(self.right_container,bg="white")
        self.r_button_container.pack(side=tk.TOP)

        # right jump_container
        self.jump_container=tk.Frame(self.right_container,bg="white")
        self.jump_container.pack(side=tk.TOP)

        # right search table
        self.table_container=tk.Frame(self.right_container,bg="white")
        self.table_container.pack(side=tk.TOP,fill=tk.BOTH)
        
        # label
        self.label = tk.Label(self.lable_frame, text="Upload a video file to extract timestamp.",bg="grey")
        self.label.pack(side=tk.TOP)

        # Assuming the class and other initialization are already defined above this
        # Select Video Button
        self.select_video_button = customtkinter.CTkButton(self.button_container, font=("Roboto", 18, "bold"), text="Upload Video", command=self.select_video)
        self.select_video_button.grid(row=0, column=0, padx=10, pady=5, sticky="w")  

        # Upload CSV/Excel Button
        self.upload_button = customtkinter.CTkButton(self.button_container,font=("Roboto", 18, "bold"), text="Upload File", command=self.upload_file)
        self.upload_button.grid(row=0, column=1, padx=10, pady=5, sticky="w") 
   
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(".")

        # Now reference the image correctly
        logo_path = os.path.join(base_path, "assets", "XOW.png")
        self.logo_image = Image.open(logo_path)  
        original_width, original_height = self.logo_image.size
        new_width = 200  
        new_height = int((new_width / original_width) * original_height)  
        self.logo_image = self.logo_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        self.logo_image_tk = ImageTk.PhotoImage(self.logo_image) 
        self.logo_label = customtkinter.CTkLabel(self.button_container, image=self.logo_image_tk, text="")  
        self.logo_label.grid(row=1, column=0, columnspan=2, pady=20, sticky="ew")  

        # Expand columns to ensure proper centering
        self.button_container.grid_columnconfigure(0, weight=1)
        self.button_container.grid_columnconfigure(1, weight=1)


        # Create a frame to hold the input widgets in a row
        self.input_frame = tk.Frame(self.search_container)
        self.input_frame.pack(side=tk.TOP, pady=(10, 20))

        # Setup Excel input widget for Fields (Column Entry)
        self.column_entry_label = tk.Label(self.input_frame, font=("Roboto",18,"bold"),text="Enter Fields:")
        self.column_entry_label.grid(row=0, column=0, padx=(10, 20), pady=5, sticky="w")  # Label for Fields

        self.column_entry = tk.Entry(self.input_frame, width=20)
        self.column_entry.grid(row=1, column=0, padx=(10, 20), pady=5, sticky="w")  
        self.column_entry.insert(0, "Enter Fields :")
        self.column_entry.config(fg='gray')
        self.column_entry.bind("<KeyRelease>", self.update_column_suggestions)

        # Setup Excel or CSV input widget for Values (Value Entry)
        self.value_entry_label = tk.Label(self.input_frame,font=("Roboto", 18,"bold"), text="Enter Value:")
        self.value_entry_label.grid(row=0, column=1, padx=(10, 20), pady=5, sticky="w")  

        self.value_entry = tk.Entry(self.input_frame, width=20)
        self.value_entry.grid(row=1, column=1, padx=(10, 20), pady=5, sticky="w")  # Input for Values
        self.value_entry.insert(0, "Enter Values :")
        self.value_entry.config(fg='gray')
        self.value_entry.bind("<KeyRelease>", self.update_value_suggestions)

        # Adding Scrollbar to the Column Listbox
        self.column_scrollbar = tk.Scrollbar(self.input_frame, orient="vertical")
        self.column_listbox = tk.Listbox(self.input_frame, height=15, yscrollcommand=self.column_scrollbar.set,width=20)
        self.column_scrollbar.config(command=self.column_listbox.yview)
        self.column_listbox.grid(row=2, column=0, padx=(10,20), pady=10, sticky="w")
        self.column_scrollbar.grid(row=2, column=0, sticky="nse")  # Scrollbar attached to the right side of the Listbox
        self.column_listbox.bind("<<ListboxSelect>>", self.select_column)

        # Adding Scrollbar to the Value Listbox
        self.value_scrollbar = tk.Scrollbar(self.input_frame, orient="vertical")
        self.value_listbox = tk.Listbox(self.input_frame, height=15, yscrollcommand=self.value_scrollbar.set,width=20)
        self.value_scrollbar.config(command=self.value_listbox.yview)
        self.value_listbox.grid(row=2, column=1, padx=(10, 20), pady=10, sticky="w")
        self.value_scrollbar.grid(row=2, column=1, sticky="nse")  # Scrollbar attached to the right side of the Listbox
        self.value_listbox.bind("<<ListboxSelect>>", self.select_value)

        # search button
        self.date_time_text = tk.Text(self.search_container, height=10, width=50)
        self.search_button = customtkinter.CTkButton(self.search_container, text="Search",font=("Roboto", 18, "bold"), command=self.search_value, fg_color="#4681f4", hover_color="#4681f4",width=140)
        self.search_button.pack(side=tk.TOP,pady=(0, 10))

        # Bind events for search entries
        # self.value_entry.bind("<KeyRelease>", self.update_value_suggestions)
        self.column_entry.bind('<FocusIn>',self.on_entry_click)
        self.column_entry.bind('<FocusOut>',self. on_focusout) 
        self.value_entry.bind('<FocusIn>',self.on_entry_click_val)
        self.value_entry.bind('<FocusOut>',self. on_focusout_val) 

        # Trim Entry Widgets
        self.start_label = tk.Label(self.trim_container,font=("Roboto", 18,"bold"), text="Download", bg="grey")
        self.start_label.pack(side=tk.TOP,pady=(0, 10))

        self.start_entry = tk.Entry(self.trim_container, width=15, font=("Roboto", 14))
        self.start_entry.insert(0, "Start Time :")
        self.start_entry.config(fg='gray')
        self.start_entry.pack(side=tk.TOP, pady=(0, 15))

        self.end_entry = tk.Entry(self.trim_container, width=15, font=("Roboto", 14))
        self.end_entry.insert(0, "End Time :")
        self.end_entry.config(fg='gray')
        self.end_entry.pack(side=tk.TOP, pady=(0, 10))

        # Bind events for trimming entries
        self.start_entry.bind('<FocusIn>', self.on_trim_click)
        self.start_entry.bind('<FocusOut>', self.on_trim)
        self.end_entry.bind('<FocusIn>', self.on_trim_click_val)
        self.end_entry.bind('<FocusOut>', self.on_trim_val)

        # Trim Button
        self.trim_button = customtkinter.CTkButton(self.trim_container,font=("Roboto", 18, "bold"), text="Download Video", command=self.trim_and_download, fg_color="#008080",height=36,width=50)
        self.trim_button.pack(side=tk.TOP)

        # Footer Label
        self.footer_label = tk.Label(
            self.left_container,
            text="Build@Punchbiz",
            bg="grey",
            fg="white",
            font=("Roboto", 10, "bold")
        )

        # Pack the footer label at the bottom of the left_container
        self.footer_label.pack(side=tk.BOTTOM, padx=10, pady=10)


        # Video Progress Bar (Below video display)
        self.progress_value = tk.DoubleVar()
        self.progress_slider = tk.Scale(self.slider_container, variable=self.progress_value, from_=0, to=100, orient="horizontal",command=self.seek)
        self.progress_slider.pack(side=tk.TOP,fill=tk.BOTH)
        self.progress_slider.configure(state="disabled")
        self.slider_in_use = False


        # initial time display
        self.initial_time_label = tk.Label(self.r_button_container, text="Initial Time :", font=("Roboto", 18,"bold"),bg="white")
        self.initial_time_label.pack(side=tk.LEFT,pady=5,padx=10)

        # Skip Button backward
        self.skip_backward_button = customtkinter.CTkButton(self.r_button_container,font=("Roboto", 18, "bold"), text="Skip -5s", command=self.skip_backward)
        self.skip_backward_button.pack(side=tk.LEFT,pady=5,padx=10)

        # Create a Tkinter button to play/pause the video
        self.play_button = customtkinter.CTkButton(self.r_button_container,font=("Roboto", 18,"bold"), text="Play", command=self.play_video, fg_color="yellow", text_color="black", hover_color="yellow")
        self.play_button.pack(side=tk.LEFT,pady=5,padx=10)


        # end time display
        self.end_time_label = tk.Label(self.r_button_container, text="End Time :", font=("Roboto", 18,"bold"),bg="white")
        self.end_time_label.pack(side=tk.RIGHT,pady=5,padx=10)

        # skip button forward
        self.skip_forward_button = customtkinter.CTkButton(self.r_button_container,font=("Roboto", 18, "bold"),text="Skip +5s", command=self.skip_forward)
        self.skip_forward_button.pack(side=tk.RIGHT,pady=5,padx=10)

        # Function to handle placeholder behavior for focus in
        def on_jump_time_entry_click(event):
            if self.jump_time_entry.get() == "Enter Time :":
                self.jump_time_entry.delete(0, "end")  # Clear the placeholder text
                self.jump_time_entry.config(fg='black')  # Set text color to black

        # Function to handle placeholder behavior for focus out
        def on_jump_time_focus_out(event):
            if self.jump_time_entry.get() == "":
                self.jump_time_entry.insert(0, "Enter Time :")  # Reinsert placeholder
                self.jump_time_entry.config(fg='gray')  # Set text color to gray

        # Jump Time Entry
        self.jump_time_entry = tk.Entry(self.jump_container, width=20, font=("Roboto", 18,"bold"), bd=2)  # bd sets the border width
        self.jump_time_entry.insert(0, "Enter Time :")
        self.jump_time_entry.config(fg='gray')  # Color set here
        self.jump_time_entry.pack(side=tk.LEFT, pady=10, padx=10)

        # Bind events to handle focus in and focus out for placeholder functionality
        self.jump_time_entry.bind("<FocusIn>", on_jump_time_entry_click)
        self.jump_time_entry.bind("<FocusOut>", on_jump_time_focus_out)


        # Jump Time Button
        self.jump_time_button = customtkinter.CTkButton(self.jump_container, font=("Roboto", 18, "bold"), text="Jump Time", command=self.jump_to_time)
        self.jump_time_button.pack(side=tk.LEFT, pady=5, padx=10)

        # Frame for search table
        self.results_frame = tk.Frame(self.table_container)
        self.results_frame.pack()
        self.results_frame.grid_rowconfigure(0, weight=1)
        self.results_frame.grid_rowconfigure(1, weight=0)
        self.results_frame.grid_columnconfigure(0, weight=1)
        self.results_frame.grid_columnconfigure(1, weight=0)

        # Start updating the progress bar
        self.update_progress()


    def on_trim_click(self, event):
        if self.start_entry.cget('fg') == 'gray':
            self.start_entry.delete(0, "end")
            self.start_entry.config(fg='black')


    def on_trim(self, event):
        if self.start_entry.get() == '':
            self.start_entry.insert(0, "Start Time :")
            self.start_entry.config(fg='gray')


    def on_trim_click_val(self, event):
        if self.end_entry.cget('fg') == 'gray':
            self.end_entry.delete(0, "end")
            self.end_entry.config(fg='black')


    def on_trim_val(self, event):
        if self.end_entry.get() == '':
            self.end_entry.insert(0, "End Time :")
            self.end_entry.config(fg='gray')
        
    
    # for trim entry        
    def on_trim_click(self,event):
        # """function that gets called whenever entry is clicked"""
        if self.start_entry.cget('fg') == 'gray':
            self.start_entry.delete(0, "end") 
            self.start_entry.insert(0, '')  
            self.start_entry.config(fg='black') 

    def on_trim(self,event):
        if self.start_entry.get() == '':
            self.start_entry.insert(0, "Start Time :")
            self.start_entry.config(fg='gray')

    def on_trim_click_val(self,event):
        # """function that gets called whenever entry is clicked"""
        if self.end_entry.cget('fg') == 'gray':
            self.end_entry.delete(0, "end") 
            self.end_entry.insert(0, '')  
            self.end_entry.config(fg='black')  

    def on_trim_val(self,event):
        if self.end_entry.get() == '':
            self.end_entry.insert(0, "End Time :")
            self.end_entry.config(fg='gray')
        

    def select_video(self):
        self.video_path = filedialog.askopenfilename(title="Select Video File", filetypes=[("MP4 files", "*.mp4")])
        if self.video_path:
            self.initial_time_str = self.get_initial_time(self.video_path)
            self.capture = cv2.VideoCapture(self.video_path)
            self.extract_times()
        else:
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)

    
    
    def on_entry_click(self,event):
        # """function that gets called whenever entry is clicked"""
        if self.column_entry.cget('fg') == 'gray':
            self.column_entry.delete(0, "end")  
            self.column_entry.insert(0, '')  
            self.column_entry.config(fg='black')  

    def on_focusout(self,event):
        if self.column_entry.get() == '':
            self.column_entry.insert(0, "Enter Fields :")
            self.column_entry.config(fg='gray')

    def on_entry_click_val(self,event):
        # """function that gets called whenever entry is clicked"""
        if self.value_entry.cget('fg') == 'gray':
            self.value_entry.delete(0, "end")  
            self.value_entry.insert(0, '')  
            self.value_entry.config(fg='black')  

    def on_focusout_val(self,event):
        if self.value_entry.get() == '':
            self.value_entry.insert(0, "Enter value :")
            self.value_entry.config(fg='gray')
        
    
    # for trim entry        
    def on_trim_click(self,event):
        # """function that gets called whenever entry is clicked"""
        if self.start_entry.cget('fg') == 'gray':
            self.start_entry.delete(0, "end") 
            self.start_entry.insert(0, '')  
            self.start_entry.config(fg='black') 

    def on_trim(self,event):
        if self.start_entry.get() == '':
            self.start_entry.insert(0, "Start Time :")
            self.start_entry.config(fg='gray')

    def on_trim_click_val(self,event):
        # """function that gets called whenever entry is clicked"""
        if self.end_entry.cget('fg') == 'gray':
            self.end_entry.delete(0, "end") 
            self.end_entry.insert(0, '')  
            self.end_entry.config(fg='black')  

    def on_trim_val(self,event):
        if self.end_entry.get() == '':
            self.end_entry.insert(0, "End Time :")
            self.end_entry.config(fg='gray')
        

    def select_video(self):
        self.video_path = filedialog.askopenfilename(title="Select Video File", filetypes=[("MP4 files", "*.mp4")])
        if self.video_path:
            self.initial_time_str = get_initial_time(self.video_path)
            self.end_time_str = get_video_end_time(self.video_path)
            print(f'This is an stat time --------> {self.initial_time_str}')
            print(f'This is an end time ----------> {self.end_time_str}')
            self.capture = cv2.VideoCapture(self.video_path)  
            media = self.vlc_instance.media_new(self.video_path)
            self.player.set_media(media)
            self.player.set_hwnd(self.canvas.winfo_id())
            # self.play_video()
            self.extract_times()
        else:
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            # self.play_video()


    def initialize_player(self):
        class Player:
            def play(self):
                print("Video playing...")
            def pause(self):
                print("Video paused...")
        return Player()

    def play_video(self):
        print("Play button clicked")
        if self.video_path:
            self.player.play()
            # Use configure instead of config
            self.play_button.configure(text="Pause", command=self.pause_video)
            
    def pause_video(self):
        print("Pause button clicked")
        self.player.pause()
        # Use configure instead of config
        self.play_button.configure(text="Play", command=self.play_video)

        
    
    def jump_to_time(self):
        if self.capture is None:
            messagebox.showerror("Error", "No video selected.")
            return

        # Get jump time and calculate jump seconds
        jump_time_str = self.jump_time_entry.get()
        
        # Convert AM/PM time to 24-hour format if necessary
        if "AM" in jump_time_str or "PM" in jump_time_str:
            jump_time_str = self.convert_to_24_hour_format(jump_time_str)

        jump_seconds = time_to_seconds(jump_time_str)
        print("Jump seconds:", jump_seconds)

        # Convert initial time to seconds
        initial_seconds = time_to_seconds(self.initial_time_str)
        
        # Debugging: check if jump and initial seconds are calculated correctly
        print(f"Jump Seconds: {jump_seconds}, Initial Seconds: {initial_seconds}")

        fps = self.capture.get(cv2.CAP_PROP_FPS)
        if fps == 0:
            messagebox.showerror("Error", "Failed to get video frame rate.")
            return

        # Calculate target seconds
        target_seconds = max(0, jump_seconds - initial_seconds)

        # Get total frames and duration
        total_frames = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
        total_duration_seconds = total_frames / fps

        # Ensure target seconds don't exceed total duration
        if target_seconds > total_duration_seconds:
            target_seconds = total_duration_seconds

        # Calculate frame position
        frame_position = int(target_seconds * fps)

        if frame_position >= total_frames:
            frame_position = total_frames - 1
        elif frame_position < 0:
            frame_position = 0

        # Set the frame to the correct position
        self.capture.set(cv2.CAP_PROP_POS_FRAMES, frame_position)
        ret, frame = self.capture.read()
        if ret:
            timestamp = extract_timestamp(frame)
            if timestamp:
                print(f"Timestamp: {timestamp}")
            else:
                print("No timestamp found.")
        else:
            print("Failed to read frame.")

        # Set the player time (in milliseconds for FFmpeg)
        self.player.set_time(int(target_seconds * 1000))


    def skip_forward(self):
            if self.capture is None:
                messagebox.showerror("Error", "No video selected.")
                return

            current_time = self.player.get_time() / 1000
            jump_seconds = 5
            new_time = current_time + jump_seconds
            self.player.set_time(int(new_time * 1000))
    
    def skip_backward(self):
        if self.capture is None:
            messagebox.showerror("Error", "No video selected.")
            return

        current_time = self.player.get_time() / 1000
        jump_seconds = 5
        new_time = max(current_time - jump_seconds, 0)
        self.player.set_time(int(new_time * 1000))

    def upload_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx; *.xls; *.csv")])
        if not file_path:
            return

        try:
            if file_path.endswith('.xlsx'):
                self.excel_data = pd.read_excel(file_path, engine='openpyxl')
            elif file_path.endswith('.xls'):
                self.excel_data = pd.read_excel(file_path, engine='xlrd')
            elif file_path.endswith('.csv'):
                self.excel_data = pd.read_csv(file_path, engine='python')
            else:
                raise ValueError("Unsupported file format. Please select a valid Excel file.")

            self.column_suggestions = list(self.excel_data.columns)
            self.value_suggestions = {
                col: self.excel_data[col].dropna().unique().tolist() for col in self.excel_data.columns
            }
            
            # Pause the video playback if the player is initialized and playing
            if hasattr(self, 'player') and self.player.is_playing():
                self.player.pause()

            # Show loading message
            loading_message_thread = threading.Thread(target=self.show_loading_message1)
            loading_message_thread.start()

            # Clear existing listbox items
            self.column_listbox.delete(0, tk.END)
            self.value_listbox.delete(0, tk.END)
            self.date_time_text.delete(1.0, tk.END)  
            
            # Populate column_listbox with column names
            for column in self.column_suggestions:
                self.column_listbox.insert(tk.END, column)

            # New logic to process the CSV file and generate output.csv
            output_file_path = 'output.csv'  
            if os.path.exists(output_file_path):
                os.remove(output_file_path)

            # Process the URLs in a separate thread to avoid blocking the UI
            processing_thread = threading.Thread(target=self.process_urls, args=(output_file_path,))
            processing_thread.start()

        except ValueError as ve:
            messagebox.showerror("Error", f"Failed to process the file: {ve}")
        except Exception as e:
            messagebox.showerror("Error", f"Please Upload the file which consists of URL column, Failed to read the Excel file!!!")


    def process_urls(self, output_file_path):
        # Open the CSV file once before the loop
        with open(output_file_path, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["Registration Number", "Full Name", "Mobile", "Company", "Designation", "Address", "City", "State", "Pincode", "Email", "Date", "Time"])
            writer.writeheader() 

            for index, url in self.excel_data['Data'].items():  
                if not url.startswith("https://www.smartexpos.in/vr/pass/"):
                    print(f"Skipping invalid URL: {url}")
                    continue
                print(f"The extracted url ---> {url}")

                try:
                    response = requests.get('http://www.google.com', timeout=5)  
                    response.raise_for_status()  
                except requests.ConnectionError:
                    messagebox.showerror("Connection Error", "No internet connection. Please check your network settings.")
                    return 
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
                }
                
                response = requests.get(url, headers=headers)

                # Check for HTTP errors
                if response.status_code != 200:
                    print(f"Error: Received status code {response.status_code}")
                    print(response.text)  
                    continue  

                # Parse the HTML content
                soup = BeautifulSoup(response.content, "html.parser")

                # Extract text from all table cells
                table = soup.find('table') 
                data_list = []

                # Check if the table was found
                if table is not None:
                    for row in table.find_all('tr'):  
                        cells = [cell.get_text(strip=True) for cell in row.find_all('td')]  
                        data_list.extend(cells)  

                # If no table is found, notify and continue to the next URL
                if not data_list:
                    print("Error: No table data found.")
                    continue

                # Parse the data
                parsed_data = parse_data(data_list)
                for col in self.excel_data.columns:
                    if col != 'Date': 
                        parsed_data[col] = self.excel_data.at[index, col]

                # Convert time columns to AM/PM format if necessary
                if 'Time' in parsed_data:
                    time_str = parsed_data['Time']
                    # Check if the time is in 24-hour format and convert if necessary
                    if self._is_valid_24_hour_format(time_str):
                        hour = int(time_str.split(':')[0])
                        if hour >= 13:  # If hour is 13 or more, convert to PM
                            time_obj = datetime.strptime(time_str, '%H:%M:%S')
                            parsed_data['Time'] = time_obj.strftime('%I:%M:%S %p')  # Convert to 12-hour format

                writer.writerow(parsed_data)
        # Close loading message
        self.hide_loading_message()
        # Resume video playback after crawling
        if hasattr(self, 'player'):
            self.player.play()

        print(f"Data has been saved to {output_file_path}")
        messagebox.showinfo("Success", "Uploaded file successfully and processed. Data saved to output.csv.")
        self.load_output_csv_for_suggestions(output_file_path)



    def convert_to_am_pm(self, time_str):
        """Convert time string to AM/PM format."""
        try:
            # Parse the time string
            time_obj = datetime.strptime(time_str, '%I:%M:%S %p')  
            return time_obj.strftime('%I:%M:%S %p')  
        except ValueError:
            return time_str  
        

    def show_loading_message1(self):
        messagebox.showinfo("Processing", "Please wait, it's crawling the URLs!!!")

    def hide_loading_message(self):
        pass

    def load_output_csv_for_suggestions(self, output_file_path):
        """Load the output CSV for further processing and suggestions."""
        if os.path.exists(output_file_path):
            self.output_data = pd.read_csv(output_file_path)
            self.column_suggestions = list(self.output_data.columns)
            self.value_suggestions = {
                col: self.output_data[col].dropna().unique().tolist() for col in self.output_data.columns
            }
            # Update the listboxes with new suggestions
            self.column_listbox.delete(0, tk.END)
            self.value_listbox.delete(0, tk.END)
            for column in self.column_suggestions:
                self.column_listbox.insert(tk.END, column)
            print("Suggestions updated based on output.csv.")
            
    # def upload_file(self):
    #     file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx; *.xls *.csv")])
    #     if not file_path:
    #         return

    #     try:
    #         if file_path.endswith('.xlsx'):
    #             self.excel_data = pd.read_excel(file_path, engine='openpyxl')
    #         elif file_path.endswith('.xls'):
    #             self.excel_data = pd.read_excel(file_path, engine='xlrd')
    #         elif file_path.endswith('.csv'):
    #             self.excel_data = pd.read_csv(file_path, engine='python')
    #         else:
    #             raise ValueError("Unsupported file format. Please select a valid Excel file.")

    #         self.column_suggestions = list(self.excel_data.columns)
    #         self.value_suggestions = {
    #             col: self.excel_data[col].dropna().unique().tolist() for col in self.excel_data.columns
    #         }

    #         # Clear existing listbox items
    #         self.column_listbox.delete(0, tk.END)
    #         self.value_listbox.delete(0, tk.END)
    #         self.date_time_text.delete(1.0, tk.END) 

    #         # Populate column_listbox with column names
    #         for column in self.column_suggestions:
    #             self.column_listbox.insert(tk.END, column)

    #         # Inform user that the file was uploaded successfully
    #         messagebox.showinfo("Success", "uploaded  file successfully. Select a column from the list.")

    #     except ValueError as ve:
    #         messagebox.showerror("Error", f"Failed to process the file: {ve}")
    #     except Exception as e:
    #         messagebox.showerror("Error", f"Failed to read the Excel file: {str(e)}")


    def seek(self, value):
        if self.capture:
            fps = self.capture.get(cv2.CAP_PROP_FPS)
            frame_position = int(float(value) * fps)
            total_frames = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if frame_position < 0:
                frame_position = 0
            elif frame_position >= total_frames:
                frame_position = total_frames - 1
            
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, frame_position)
            self.play_video()         
        
    def search_value(self):
        # Load the output CSV data if not already loaded
        if not hasattr(self, 'output_data'):
            try:
                self.output_data = pd.read_csv('output.csv')  
            except FileNotFoundError:
                messagebox.showerror("Error", "Output file not found.")
                return

        column_name = self.column_entry.get()
        value = self.value_entry.get()

        if column_name in self.output_data.columns:  
            filtered_df = self.output_data[self.output_data[column_name] == value]  

            # Create Treeview widget only when search button is clicked
            columns = list(filtered_df.columns)
            self.tree = ttk.Treeview(self.results_frame, columns=columns, show='headings')

            # Set the headings dynamically
            for column in columns:
                self.tree.heading(column, text=column)

            # Scrollbars
            self.h_scroll = ttk.Scrollbar(self.results_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
            self.v_scroll = ttk.Scrollbar(self.results_frame, orient=tk.VERTICAL, command=self.tree.yview)

            self.tree.grid(row=0, column=0, sticky="news")
            self.h_scroll.grid(row=2, column=0, sticky="we")
            self.v_scroll.grid(row=0, column=1, sticky="ns")

            self.tree.configure(xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)

            # Set column widths dynamically based on data
            for column in columns:
                self.tree.column(column, width=220, anchor='center')

            # Style for Treeview
            style = ttk.Style()
            style.theme_use('clam')

            # Set row height to match Excel-like spacing (adjust as needed)
            style.configure('Treeview', rowheight=30, highlightbackground="black", highlightthickness=2)
            style.configure("Treeview.Heading", font=("Arial", 12, "bold"))
            style.configure("Treeview", font=("Arial", 12))

            # Bind selection event
            self.tree.bind("<<TreeviewSelect>>", self.on_item_selected)

            # Insert actual rows
            for index, row in filtered_df.iterrows():
                self.tree.insert("", tk.END, values=list(row))

            if filtered_df.empty:
                messagebox.showinfo("No Results", "No matching results found.")
        else:
            messagebox.showerror("Error", "Column name not found in the output file.")



    def update_column_suggestions(self, event):
        """Updates the column listbox based on the text in the column_entry."""
        search_text = self.column_entry.get().lower()
        self.column_listbox.delete(0, tk.END)
        
        if search_text:
            # Suggest columns based on the search text
            suggestions = [col for col in self.column_suggestions if search_text in col.lower()]
            for suggestion in suggestions:
                self.column_listbox.insert(tk.END, suggestion)

    def update_value_suggestions(self, event):
        """Updates the value listbox with all values based on the selected column or filters them based on user input."""
        # Get the selected column
        selected_column = self.column_entry.get()
        if selected_column and selected_column in self.value_suggestions:
            # Get the values for the selected column
            values = self.value_suggestions[selected_column]
            self.value_listbox.delete(0, tk.END)
            suggestions=values
            for suggestion in suggestions:
                    self.value_listbox.insert(tk.END, suggestion)

    def update_val_suggestions(self, event):
        """Updates the column listbox based on the text in the column_entry."""
        search_text = self.value_entry.get().lower()
        selected_column = self.column_entry.get()
        if selected_column and selected_column in self.value_suggestions:
            if search_text:
                    self.value_listbox.delete(0, tk.END)
                    values = self.value_suggestions[selected_column]
                    # Suggest columns based on the search text
                    suggestions = [val for val in values if search_text in str(val).lower()]
                    for suggestion in suggestions:
                        self.value_listbox.insert(tk.END, suggestion)

    def select_column(self, event):
        """Handles the selection of a column from the column listbox and updates value suggestions."""
        selection = self.column_listbox.curselection()
        if selection:
            column_name = self.column_listbox.get(selection[0])
            self.column_entry.delete(0, tk.END)
            self.column_entry.insert(0, column_name)
            
            # Immediately update the value suggestions based on the selected column
            self.update_value_suggestions(None)

    def select_value(self, event):
        """Handles the selection of a value from the value listbox."""
        selection = self.value_listbox.curselection()
        if selection:
            value = self.value_listbox.get(selection[0])
            self.value_entry.delete(0, tk.END)
            self.value_entry.insert(0, value)
            
            # Update the start time based on selected value
            self.start_entry.delete(0, tk.END)
            self.start_entry.insert(0, value)
            
            # Set the end time to the video duration (example end time used)
            self.end_entry.delete(0, tk.END)
            self.end_entry.insert(0, self.end_time_str)


    def on_item_selected(self, event):
        """Handles selection of an item from the treeview."""
        if not self.video_path:  # Check if video_path is None
            messagebox.showerror("Error", "Please upload a video file to start the process.")
            return

        selected_item = self.tree.selection()
        self.initial_time_str = get_initial_time(self.video_path)
        self.end_time_str = get_video_end_time(self.video_path)
        
        if selected_item:
            item_values = self.tree.item(selected_item)["values"]
            columns = list(self.output_data.columns)  
            possible_columns = ["Registration Number", "Full Name", "Mobile", "Company", "Designation", "Address", "City", "State", "Pincode", "Email", "Date", "Time"]
            timestamp_column_index = None

            # Find the index of the timestamp column
            for col in possible_columns:
                if col in columns:
                    timestamp_column_index = columns.index(col)
                    break

            if timestamp_column_index is None:
                raise ValueError("No timestamp column found.")

            # Access the timestamp from the last index of item_values
            timestamp_value = item_values[-1] 
            
            # Debugging: Check the contents of item_values
            print(f"Item values: {item_values}")
            print(f"Timestamp value before stripping: {timestamp_value} (type: {type(timestamp_value)})")
            
            # Ensure the timestamp is treated as a string
            if isinstance(timestamp_value, int):
                timestamp_value = str(timestamp_value)

            timestamp = timestamp_value.strip() 
            print(f"Selected Timestamp: '{timestamp}'")  
            
            # Convert strings to datetime objects for comparison
            selected_time = parse_time(timestamp)
            initial_time = parse_time(self.initial_time_str)
            end_time = parse_time(self.end_time_str)

            if selected_time is None or initial_time is None or end_time is None:
                print(f"Error parsing times. Selected: {selected_time}, Initial: {initial_time}, End: {end_time}")  # Debugging line
                messagebox.showinfo("Error", "Could not parse time.")
                return
            
            print(f"Parsed Selected Time: {selected_time}")
            print(f"Parsed Initial Time: {initial_time}")
            print(f"Parsed End Time: {end_time}")

            # Convert times to seconds for comparison
            selected_time_seconds = self.time_to_seconds(selected_time)  
            initial_time_seconds = self.time_to_seconds(initial_time)
            end_time_seconds = self.time_to_seconds(end_time)

            # Compare times and handle errors
            if selected_time_seconds > end_time_seconds:
                messagebox.showinfo("Error", "Selected time exceeds the end time.")
            elif selected_time_seconds < initial_time_seconds:
                messagebox.showinfo("Error", "Selected time is before the initial time.")
            else:
                self.jump_time_entry.delete(0, tk.END)
                self.jump_time_entry.insert(0, timestamp)
                self.jump_to_time() 
                self.start_entry.delete(0, tk.END)
                self.start_entry.insert(0, timestamp)
                self.end_entry.delete(0, tk.END)
                self.end_entry.insert(0, self.end_time_str)  



    def extract_times(self):
        if self.video_path:
            self.initial_time_str = get_initial_time(self.video_path)
            self.end_time_str = get_video_end_time(self.video_path)
            
            self.initial_time_label.configure(text=f"Initial Time: {self.initial_time_str}")
            self.end_time_label.configure(text=f"End Time: {self.end_time_str}")
            self.update_progress()
            self.play_video()


    def update_progress(self):
            if self.player.is_playing() and not self.slider_in_use:  
                length = self.player.get_length() / 1000  
                current_time = self.player.get_time() / 1000  

                # Calculate progress as a percentage
                if length > 0:
                    progress = (current_time / length) * 100
                    self.progress_value.set(progress)  

                # Check if the video has reached the end
                if current_time >= length:
                    self.player.pause()  
                    self.slider_in_use = False  

                    # Display a success message when the video ends
                    if not hasattr(self, 'video_ended_displayed') or not self.video_ended_displayed:
                        messagebox.showinfo("Video Ended", "The video has ended successfully.")
                        self.video_ended_displayed = True  
            self.root.after(100, self.update_progress)

    def _is_valid_24_hour_format(self, time_str):
        """Check if the time is in HH:MM:SS format using a regex pattern."""
        time_pattern_24hr = r'^(?:[01]?\d|2[0-3]):[0-5]\d(:[0-5]\d)?$'  # 24-hour format with optional seconds
        return bool(re.match(time_pattern_24hr, time_str))

    def _is_valid_time_format(self, time_str):
        """Check if the time is in HH:MM:SS or HH:MM:SS AM/PM format using a regex pattern."""
        time_pattern_12hr = r'^(0?[1-9]|1[0-2]):[0-5][0-9] [APap][mM]$'  
        time_pattern_24hr = r'^(?:[01]?\d|2[0-3]):[0-5]\d:[0-5]\d$'  
        time_pattern_no_am_pm = r'^(0?[1-9]|1[0-2]):[0-5][0-9]$'  

        # Check if the time string matches any of the patterns
        is_valid = (bool(re.match(time_pattern_12hr, time_str)) or 
                     bool(re.match(time_pattern_24hr, time_str)) or 
                     bool(re.match(time_pattern_no_am_pm, time_str)))

        # Debugging: Print the result of the validation
        print(f"Validating time '{time_str}': {is_valid}")
        return is_valid

    def trim_and_download(self):
        if not self.video_path:
            messagebox.showerror("Error", "No video selected.")
            return

        # Pause the video playback
        self.player.pause()

        # Show a message indicating that the video is being trimmed
        messagebox.showinfo("Please Wait", "The video is being trimmed...")

        start_time = self.start_entry.get().strip()  # Strip whitespace
        print(f"The start time from trim option: '{start_time}'")
        end_time = self.end_entry.get().strip()  # Strip whitespace
        print(f"The End time from trim option: '{end_time}'")
        start_time = re.sub(r'(?i)\s*[APap][Mm]', '', start_time).strip() 
        print(f"The start time from trim after removal of AM/PM: '{start_time}'")
        end_time = re.sub(r'(?i)\s*[APap][Mm]', '', end_time).strip()
        print(f"The end time from trim after removal of AM/PM: '{start_time}'")

        # Validate start_time and end_time
        if not self._is_valid_time_format(start_time):
            messagebox.showerror("Time Error", f"Invalid Start Time: '{start_time}'. Please use HH:MM:SS or HH:MM:SS AM/PM.")
            return

        if not self._is_valid_time_format(end_time):
            messagebox.showerror("Time Error", f"Invalid End Time: '{end_time}'. Please use HH:MM:SS or HH:MM:SS AM/PM.")
            return


        print("Starting the trimming process...")
        print(f"Initial Time: {self.initial_time_str}, Start Time: {start_time}, End Time: {end_time}")

        # Run the trimming process in a separate thread
        def process_video():
            trimmed_file = trim_video(self.video_path, start_time, end_time, self.initial_time_str)
            def update_ui():
                if trimmed_file:
                    messagebox.showinfo("Success", f"Trimmed video saved as {trimmed_file}")
                else:
                    messagebox.showerror("Error", "Failed to trim video.")
            self.root.after(0, update_ui) 

        threading.Thread(target=process_video).start()

    def convert_to_24_hour_format(self, time_str):
        """Convert a time string from AM/PM format to 24-hour format, if needed."""
        try:
            if re.match(r'^\d{2}:\d{2}:\d{2}$', time_str):  # Already 24-hour format
                return time_str
            # Parse as 12-hour format with AM/PM
            time_obj = datetime.strptime(time_str, '%I:%M:%S %p')
            return time_obj.strftime('%H:%M:%S')
        except ValueError:
            return time_str  # Return the original if it fails


    def time_to_seconds(self, time_str):
        print(f'Time to convert: {time_str}')
        try:
            # Check if the input is a datetime object
            if isinstance(time_str, datetime):
                # If it's a datetime object, extract the total seconds
                total_seconds = time_str.hour * 3600 + time_str.minute * 60 + time_str.second
                return total_seconds

            # Check if the time string contains AM or PM
            if 'AM' in time_str or 'PM' in time_str:
                # Handle time that contains 'AM' or 'PM'
                time_obj = datetime.strptime(time_str, '%I:%M:%S %p')  # Assuming input is in HH:MM:SS AM/PM format
            else:
                # Handle 24-hour format
                time_obj = datetime.strptime(time_str, '%H:%M:%S')

            # Calculate total seconds
            total_seconds = time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second
            return total_seconds

        except ValueError:
            messagebox.showerror("Time Error", "Time format not recognized.")
            raise ValueError(f"Time format not recognized: {time_str}")


if __name__ == "__main__":
    root = customtkinter.CTk()
    app = VideoPlayerApp(root)
    root.mainloop()
