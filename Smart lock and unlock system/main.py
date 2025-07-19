import tkinter as tk
from tkinter import messagebox
import pandas as pd
import cv2
import os
from deepface import DeepFace
import threading
from datetime import datetime, time
import serial
import time
# Define start and end times for attendance
# start_time = time(11, 0)
# end_time = time(11, 55)  

try:
    ser = serial.Serial('COM8', 9600, timeout=1)  # Adjust 'COM3' to your serial port
except Exception as e:
    ser = None
    print(f"Serial connection failed: {e}")
global hr,spo2,temp,sstatus
hr=0
spo2=0
temp=0
sstatus=""

# Function to mark attendance as "Absent" after the end time
def mark_absent_after_end_time():
    global attendance_df
    global hr,spo2,temp,sstatus

    while True:
        try:
            sdata=ser.readlines()
            time.sleep(2)
            sdata=sdata[0].decode('utf-8').strip()
            ldata=sdata.split(',')
            hr=int(ldata[0])
            spo2=int(ldata[1])
            temp=int(ldata[2])
            sstatus=ldata[3]

            print("sdata",ldata)
        except Exception as e:
            print("error",str(e))

            # break  # Stop the loop (run only once after the end time)


# Function to register student
def register_student():
    student_name = name_entry.get()
    if student_name:
        # Capture image of the student
        capture_student_image(student_name)
    else:
        messagebox.showerror("Error", "Please enter a valid student name.")

# Function to capture and save student image
def capture_student_image(student_name):
    # Open webcam
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        messagebox.showerror("Error", "Failed to open webcam.")
        return

    # Capture frame
    for i in range(20):
        ret, frame = cap.read()
    cap.release()

    # Save image to student_images directory
    image_path = os.path.join("student_images", f"{student_name}.jpg")
    cv2.imwrite(image_path, frame)
    messagebox.showinfo("Success", f"Image of {student_name} saved successfully!")


# Function to recognize student from captured image
def recognize_student():
    try:
        # Open webcam
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            messagebox.showerror("Error", "Failed to open webcam.")
            return

        # Capture frame
        for i in range(10):
            ret, frame = cap.read()
        cap.release()

        # Save image to current_image.jpg
        image_path = 'current_image.jpg'
        cv2.imwrite(image_path, frame)

        # Load the captured image
        captured_image = cv2.imread(image_path)

        # Load the saved student images from the database
        saved_student_images = []
        for root, dirs, files in os.walk("student_images"):
            for file in files:
                if file.endswith(".jpg"):
                    saved_student_images.append(os.path.join(root, file))

        # Compare the captured image with the saved student images
        if(len(saved_student_images)>0):
            for saved_image_path in saved_student_images:
                verification = DeepFace.verify(img1_path=saved_image_path, img2_path=image_path)
                print(verification)
                if verification['verified']:
                    if(verification['distance']<0.4):
                        student_name = os.path.basename(saved_image_path).split('.')[0]
                        register_attendance(student_name)
                        fc=verification['facial_areas']['img2']
                        face_coordinates = (fc['x'], fc["y"], fc["w"], fc["h"]) 

                        # Draw a rectangle around the face
                        cv2.rectangle(captured_image, (face_coordinates[0], face_coordinates[1]), (face_coordinates[0] + face_coordinates[2], face_coordinates[1] + face_coordinates[3]), (0, 255, 0), 2)

                        # Put the person's name below the rectangle
                        cv2.putText(captured_image, student_name, (face_coordinates[0], face_coordinates[1] + face_coordinates[3] + 20), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
            cv2.imshow('att',captured_image)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("")
        else:
            messagebox.showerror("Error", "No student recognized in the captured image.")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {str(e)}")


def register_attendance1(student_name):
    global attendance_df  # Declare attendance_df as a global variable
    
    try:
        # Check current time
        current_time = datetime.now().strftime('%H:%M:%S')
        
        # Check if the student has already registered an in-time for today
        today = datetime.now().strftime('%Y-%m-%d')
        existing_record = attendance_df[(attendance_df['Student Name'] == student_name) & (attendance_df['Date'] == today)]

        if not existing_record.empty:
            # Student already has a record for today
            messagebox.showinfo("Info", f"{student_name} already has a record for today.")
            return

        # Mark student as absent initially
        attendance_df = attendance_df.append({'Student Name': student_name, 'P/A': 'A', 'Date': today}, ignore_index=True)
        
        # Check if the current time is before 10 am, then mark student as present
        if today == today:
            attendance_df.loc[(attendance_df['Student Name'] == student_name) & (attendance_df['Date'] == today), 'P/A'] = 'P'
            

        attendance_df.to_csv('attendance.csv', index=False)
        messagebox.showinfo("Success", f"{student_name}'s attendance registered successfully!")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {str(e)}")

def register_attendance(student_name):
    global attendance_df

    try:
        current_time = datetime.now().time()
        current_date = datetime.now().strftime('%Y-%m-%d')

        # Check if the student has already registered attendance for today
        existing_record = attendance_df[
            (attendance_df['Student Name'] == student_name) & 
            (attendance_df['Date'] == current_date)
        ]

        # if not existing_record.empty:
        #     messagebox.showinfo("Info", f"{student_name} already has a record for today.")
        #     return

        # Determine if the student is "Present" or "Absent" based on the time
        status = "P"

        # Add the attendance record
        attendance_df = attendance_df.append(
            {
                'Student Name': student_name,
                'P/A': "P",
                'Date': current_date,
                'In Time': datetime.now().strftime('%H:%M:%S') if status == "P" else "N/A",
                'Heart rate':hr,
                'SPO2':spo2,
                'Temperature':temp,
                'Status':sstatus
            },
            ignore_index=True
        )

        # Save the updated attendance record to CSV
        attendance_df.to_csv('attendance.csv', index=False)
        
        # Notify the user
        if status == "P":
            messagebox.showinfo("Success", f"{student_name} marked as Present!")
        else:
            messagebox.showwarning("Late", f"{student_name} marked as Absent (Late)!")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {str(e)}")

# Function to display webcam feed and recognize student
def show_webcam():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        messagebox.showerror("Error", "Failed to open webcam.")
        return

    while True:
        for i in range(10):
            ret, frame = cap.read()
        if not ret:
            messagebox.showerror("Error", "Failed to capture frame.")
            break

        cv2.imshow('Webcam', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        if cv2.waitKey(1) & 0xFF == ord('r'):
            recognize_student()

    cap.release()
    cv2.destroyAllWindows()

# //////////////////////////////
# Function to preview face
def preview_face():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        messagebox.showerror("Error", "Failed to open webcam.")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            messagebox.showerror("Error", "Failed to capture frame.")
            break

        cv2.imshow("Preview Face - Press 'q' to Exit", frame)
        if cv2.waitKey(1) & 0xFF == ord('c'):
            register_student()
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


# //////////////////////////////




# GUI
root = tk.Tk()
root.title("Attendance System")
root.configure(bg="lightblue")

name_label = tk.Label(root, text="Name:")
name_label.grid(row=0, column=0, padx=35, pady=20)

name_entry = tk.Entry(root)
name_entry.grid(row=0, column=1, padx=50, pady=30)

register_student_button = tk.Button(root, text="Train", command=register_student)
register_student_button.grid(row=1, column=0, columnspan=2, padx=40, pady=20, sticky="WE")

show_webcam_button = tk.Button(root, text="Press 'r' to Capture", command=show_webcam)
show_webcam_button.grid(row=2, column=0, columnspan=2, padx=70, pady=40, sticky="WE")


preview_face_button = tk.Button(root, text="Preview Face", command=preview_face)
preview_face_button.grid(row=3, column=0, columnspan=2, padx=40, pady=30, sticky="WE")

# Load existing attendance data
try:
    attendance_df = pd.read_csv('attendance.csv')
except FileNotFoundError:
    attendance_df = pd.DataFrame(columns=['Student Name', 'P/A', 'Date', 'In Time','Heart rate','SPO2','Temperature','Status'])

# Create student_images directory if it doesn't exist
if not os.path.exists("student_images"):
    os.makedirs("student_images")

threading.Thread(target=mark_absent_after_end_time, daemon=True).start()

root.mainloop()